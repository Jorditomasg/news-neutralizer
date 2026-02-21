import re

def compute_approximate_tokens(text: str) -> int:
    """Approximate token count (1 token ≈ 4 chars for languages like Spanish/English)."""
    return len(text) // 4

def segment_text_into_chunks(text: str, max_tokens: int = 1500) -> list[str]:
    """
    Segment text into chunks maximizing max_tokens.
    Strict rule: Never split mid-paragraph. Uses `\n` or `.` as boundaries.
    """
    if not text:
        return []

    # 1. Split by paragraphs first
    paragraphs = [p.strip() for p in re.split(r'\n+', text) if p.strip()]
    
    chunks = []
    current_chunk = []
    current_tokens = 0
    
    for paragraph in paragraphs:
        p_tokens = compute_approximate_tokens(paragraph)
        
        # If a single paragraph is larger than max_tokens, we still must not break the 
        # "do not split mid-paragraph" rule, but practically we might have to break it into sentences.
        # But per user instructions: "Nunca segmentar a la mitad de un párrafo por grande que sea. 
        # Se utilizará la puntuación natural (., \n) como punto de corte exclusivo para no mutilar el contexto."
        if p_tokens > max_tokens:
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_tokens = 0
            # We must break it by sentences (.)
            sentences = [s.strip() + "." for s in paragraph.split(".") if s.strip()]
            for sentence in sentences:
                s_tokens = compute_approximate_tokens(sentence)
                if current_tokens + s_tokens > max_tokens and current_chunk:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = [sentence]
                    current_tokens = s_tokens
                else:
                    current_chunk.append(sentence)
                    current_tokens += s_tokens
            continue

        if current_tokens + p_tokens > max_tokens and current_chunk:
            # Finish the current chunk
            chunks.append("\n\n".join(current_chunk))
            current_chunk = [paragraph]
            current_tokens = p_tokens
        else:
            current_chunk.append(paragraph)
            current_tokens += p_tokens
            
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
        
    return chunks
