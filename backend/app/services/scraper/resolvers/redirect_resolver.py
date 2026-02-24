import asyncio
import re
import base64
from urllib.parse import urlparse, urljoin
import httpx
import structlog
from bs4 import BeautifulSoup

logger = structlog.get_logger(__name__)

class RedirectResolver:
    """
    Follows HTTP redirects and bypasses intermediate consent walls or JS redirects
    to find the true canonical URL of an article.
    """

    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )

    MAX_REDIRECTS = 5

    async def _resolve_fast_path(self, url: str) -> str | None:
        """
        Decode Google News URLs (`/rss/articles/`) to their canonical forms
        using googlenewsdecoder. This handles the latest CBM formats.
        """
        parsed = urlparse(url)
        if "news.google.com" in parsed.netloc and "/rss/articles/" in parsed.path:
            try:
                import googlenewsdecoder
                # The decoder does HTTP requests internally to resolve the redirect
                # Wrap it in wait_for to prevent indefinite hangs
                logger.info("Starting googlenewsdecoder.new_decoderv1", url=url)
                result = await asyncio.wait_for(
                    asyncio.to_thread(googlenewsdecoder.new_decoderv1, url),
                    timeout=10.0
                )
                logger.info("googlenewsdecoder result", result=result)
                if result and result.get("status") and result.get("decoded_url"):
                    real_url = result["decoded_url"]
                    logger.info("Decoded Google News URL natively", original=url, resolved=real_url)
                    return real_url
            except Exception as e:
                logger.warning("Failed to native-decode Google News URL", error=str(e), exc_info=True)
        return None

    async def resolve(self, url: str) -> str:
        """
        Takes an initial URL and follows it through HTTP redirects and HTML/JS
        auto-redirects to find the final effective article URL.
        """
        # 1. Native fast-path check
        fast_path_url = await self._resolve_fast_path(url)
        if fast_path_url:
            url = fast_path_url

        current_url = url
        redirect_count = 0

        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True, # Handles basic HTTP 3xx redirects automatically
            headers={
                "User-Agent": self.USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
                "Sec-Ch-Ua": '"Not A(Brand";v="8", "Chromium";v="132", "Brave";v="132"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "cross-site",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1"
            },
            cookies={"CONSENT": "YES+cb.20230101-14-p0.en+FX+430"}, # Generic Google/Tracking consent bypass
        ) as client:
            while redirect_count < self.MAX_REDIRECTS:
                logger.info("Resolving URL", url=current_url, redirect_count=redirect_count)
                try:
                    # We use GET to fetch content to analyze for consent walls
                    response = await client.get(current_url)
                    response.raise_for_status()
                    
                    # Ensure current_url represents the end of any HTTP 3xx redirects
                    current_url = str(response.url)
                    
                    html = response.text
                    
                    # 1. Check for canonical link first
                    canonical = self._extract_canonical(html, current_url)
                    
                    # 2. Check if this is an intermediate consent wall / JS redirect
                    next_url = self._extract_intermediate_redirect(html, current_url)
                    
                    if next_url and next_url != current_url:
                        # Follow the intermediate redirect
                        logger.info("Detected intermediate wall/redirect", current_url=current_url, next_url=next_url)
                        current_url = next_url
                        
                        if "news.google.com" in current_url:
                            fast_url = await self._resolve_fast_path(current_url)
                            if fast_url:
                                logger.info("Decoded Google News URL natively after intermediate redirect", original=current_url, resolved=fast_url)
                                current_url = fast_url
                                continue
                                
                        redirect_count += 1
                        continue
                    
                    # If we made it here, no intermediate html redirect was found. 
                    # Prefer canonical if found, else return the final resolved URL
                    resolved_url = canonical if canonical else current_url
                    
                    fast_url = await self._resolve_fast_path(resolved_url)
                    if fast_url:
                        logger.info("Decoded Google News URL natively after resolving canonical", original=resolved_url, resolved=fast_url)
                        return fast_url
                        
                    logger.info("URL resolved successfully", final_url=resolved_url)
                    return resolved_url

                except httpx.HTTPError as e:
                    logger.error("Failed to resolve URL", url=current_url, error=str(e))
                    return current_url # Return as deep as we got on network error
                except Exception as e:
                    logger.error("Unexpected error resolving URL", url=current_url, error=str(e))
                    return current_url
                    
        logger.warning("Max redirects reached", initial_url=url, final_url=current_url)
        return current_url

    def _extract_canonical(self, html: str, base_url: str) -> str | None:
        """Extract canonical URL from HTML."""
        soup = BeautifulSoup(html, "lxml")
        canonical_tag = soup.find("link", rel="canonical")
        if canonical_tag and canonical_tag.get("href"):
            return urljoin(base_url, str(canonical_tag["href"])).strip()
        
        og_url = soup.find("meta", property="og:url")
        if og_url and og_url.get("content"):
             return urljoin(base_url, str(og_url["content"])).strip()
             
        return None

    def _extract_intermediate_redirect(self, html: str, base_url: str) -> str | None:
        """
        Detects if the page is a consent wall, cookie page, or JS redirect,
        and extracts the destination URL if possible.
        """
        soup = BeautifulSoup(html, "lxml")
        
        # 1. Meta Refresh
        # <meta http-equiv="refresh" content="0; url=https://example.com/actual-news">
        meta_refresh = soup.find("meta", attrs={"http-equiv": lambda x: x and str(x).lower() == "refresh"})
        if meta_refresh:
            content = meta_refresh.get("content", "")
            match = re.search(r'url\s*=\s*[\'"]?([^\'"/][^\'"\s]+)', str(content), re.IGNORECASE)
            if match:
                 return urljoin(base_url, match.group(1))
                 
        # 2. Google-specific Consent Wall (or general consent forms)
        # Usually contains text "Before you continue" or form action pointing to consent
        text_lower = html.lower()
        if "before you continue to google" in text_lower or "consent.google.com" in base_url.lower():
            # In Google's consent wall, there's usually a form to accept, or a link hiding the continue URL
            # But the actual destination is sometimes buried in a continue= parameter or a JS variable.
            # Let's try to parse the continue parameter from the base_url
            parsed_url = urlparse(base_url)
            from urllib.parse import parse_qs
            qs = parse_qs(parsed_url.query)
            if "continue" in qs:
                return qs["continue"][0]
        
        # 3. Simple JS Redirects (window.location.replace, window.location.href)
        # Often seen on very short pages (less than 2000 chars of HTML)
        if len(html) < 5000:
             # Basic pattern for JS redirect
             js_match = re.search(r'window\.location\.(?:replace|href)\s*=\s*[\'"]([^\'"]+)[\'"]', html)
             if js_match:
                 return urljoin(base_url, js_match.group(1))
                 
        # 4. Consent wall data-url attributes or similar (catch-all for common tracking click-throughs)
        # Sometimes intermediate ad-click trackers just put the link in an obvious 'a' tag if js is disabled
        noscript = soup.find("noscript")
        if noscript:
             noscript_a = noscript.find("a", href=True)
             if noscript_a and 'href' in noscript_a.attrs:
                  # If the noscript tag is the only real content on the page, it's a redirect
                  # We'll check if there are no main text paragraphs
                   if not soup.find("p"):
                        return urljoin(base_url, str(noscript_a["href"]))

        return None
