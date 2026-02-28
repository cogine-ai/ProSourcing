from bs4 import BeautifulSoup
import re

def extract_algatop():
    with open("d:/item/ProSourcing/output/algatop_product_dom.html", "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    
    # Remove script and style elements
    for script in soup(["script", "style", "svg"]):
        script.extract()
        
    # Get all text blocks and look for numbers next to labels
    text_blocks = soup.stripped_strings
    text_blocks = list(text_blocks)
    
    for i, t in enumerate(text_blocks):
        if any(kw in t.lower() for kw in ["выручка", "продажи", "дней", "средний", "cr3", "продавцов", "бренд"]):
            # print surrounding texts
            context = text_blocks[max(0, i-3):min(len(text_blocks), i+4)]
            print(f"[{i}] {t}")
            print(" Context:", " | ".join(context))
            print("-" * 50)
            
if __name__ == "__main__":
    extract_algatop()
