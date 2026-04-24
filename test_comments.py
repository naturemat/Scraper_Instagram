# test_comments.py
import asyncio
import os
from dotenv import load_dotenv
from playwright.async_api import async_playwright

load_dotenv()

async def test_comments():
    session_id = os.getenv("IG_SESSION_ID")
    csrftoken = os.getenv("IG_CSRFTOKEN")
    shortcode = "DNcAqJ-u9eh"
    
    print(f"Testing comments for post: {shortcode}")
    print("-" * 50)
    
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    
    context = await browser.new_context(
        storage_state={
            "cookies": [
                {
                    "name": "sessionid",
                    "value": session_id,
                    "domain": ".instagram.com",
                    "path": "/"
                },
                {
                    "name": "csrftoken",
                    "value": csrftoken,
                    "domain": ".instagram.com",
                    "path": "/"
                }
            ]
        },
        viewport={"width": 1280, "height": 720}
    )
    
    page = await context.new_page()
    
    try:
        url = f"https://www.instagram.com/p/{shortcode}/"
        print(f"Loading: {url}")
        
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        
        # Wait for the page to load
        await page.wait_for_timeout(8000)
        
        # Scroll to load all comments
        for _ in range(4):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)
        
        # Extract comments with deduplication
        comments_data = await page.evaluate("""
            () => {
                const comments = new Map();
                const mainContainer = document.querySelector('div.x9f619.x1n2onr6.x1ja2u2z');
                if (!mainContainer) return [];
                
                const commentDivs = mainContainer.querySelectorAll('div.html-div');
                
                for (const div of commentDivs) {
                    const userLink = div.querySelector('a[href^="/"][class*="notranslate"], a[href^="/"]');
                    if (!userLink) continue;
                    
                    const username = userLink.innerText.trim();
                    if (!username || username === '' || username === '_mari1_7') continue;
                    
                    const allSpans = div.querySelectorAll('span');
                    let commentText = '';
                    
                    for (const span of allSpans) {
                        const text = span.innerText.trim();
                        const isTimestamp = /^\\d+\\s*(sem|w|d|h|min|ago)$/i.test(text);
                        const isAction = text.includes('Me gusta') || text.includes('Responder') || text.includes('Ver traducción');
                        
                        if (text && 
                            text !== username &&
                            !isTimestamp && 
                            !isAction &&
                            text.length > 2) {
                            commentText = text;
                            break;
                        }
                    }
                    
                    if (commentText) {
                        const key = username + '|' + commentText;
                        if (!comments.has(key)) {
                            comments.set(key, { username: username, text: commentText });
                        }
                    }
                }
                
                return Array.from(comments.values());
            }
        """)
        
        print(f"\nFound {len(comments_data)} unique comments:")
        for i, c in enumerate(comments_data[:15], 1):
            print(f"{i}. @{c['username']}: {c['text'][:80]}")
        
        input("\nPress Enter to close browser...")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await browser.close()
        await playwright.stop()

if __name__ == "__main__":
    asyncio.run(test_comments())