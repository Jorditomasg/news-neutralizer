import httpx
import asyncio
import sys

# Inside the container, localhost:8000 is correct for the service itself (it listens on 0.0.0.0)
API_URL = "http://localhost:8000/api/v1"

async def test_url_search(url):
    print(f"Testing URL search for: {url}")
    
    async with httpx.AsyncClient() as client:
        # 1. Start Search
        resp = await client.post(f"{API_URL}/search/", json={"query": url})
        if resp.status_code != 200:
            print(f"FAILED to start search: {resp.status_code} {resp.text}")
            return False
        
        task_id = resp.json()["task_id"]
        print(f"Task started: {task_id}")
        
        # 2. Poll for results
        for _ in range(60):  # Wait up to 120 seconds
            await asyncio.sleep(2)
            try:
                resp = await client.get(f"{API_URL}/search/{task_id}")
            except Exception as e:
                print(f"Error polling: {e}")
                continue
                
            if resp.status_code != 200:
                print(f"Error polling task: {resp.status_code}")
                continue
                
            data = resp.json()
            status = data["status"]
            print(f"Status: {status}, Progress: {data.get('progress')}%")
            
            if status == "completed":
                print("Task completed!")
                # 3. Verify results
                source = data.get("source_article")
                if not source:
                    print("FAILED: source_article is missing!")
                    return False
                
                print(f"Source article found: {source['title']}")
                
                articles = data.get("articles", [])
                if not articles:
                     print("FAILED: No articles found!")
                     return False
                
                source_in_list = any(a.get("is_source") for a in articles)
                if not source_in_list:
                    print("FAILED: Source article not marked in articles list!")
                    return False
                    
                print(f"Total articles: {len(articles)}")
                print("Success!")
                return True
                
            if status == "failed":
                print(f"Task FAILED: {data.get('error_message')}")
                return False
                
        print("Timed out waiting for task completion")
        return False

if __name__ == "__main__":
    # Use a real URL that works. Assuming internet access.
    # El Pais or BBC or similar.
    test_url = "https://elpais.com/internacional/2024-02-15/rusia-lanza-un-ataque-masivo-con-misiles-contra-varias-ciudades-de-ucrania.html" 
    # Fallback to something simpler if that fails? No, let's try.
    
    success = asyncio.run(test_url_search(test_url))
    sys.exit(0 if success else 1)
