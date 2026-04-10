
import asyncio
from core.final_pipeline import supabase as sb
from deep_translator import GoogleTranslator

async def translate_categories():
    print("Starting batch translation of leaf categories...")
    
    # 1. Fetch only leaf categories that don't have Chinese in their names
    # We assume Chinese characters are present if there's a '(' or common Chinese characters
    # But to be safe, we'll fetch all leaf categories (is_has_subcategory=0)
    res = sb.table("categories").select("category_id, category_name").eq("is_has_subcategory", 0).execute()
    leaves = res.data
    print(f"Total leaf categories to check: {len(leaves)}")
    
    translator = GoogleTranslator(source='ru', target='zh-CN')
    
    count = 0
    for leaf in leaves:
        original_name = leaf['category_name']
        
        # Check if it's already bilingual (contains Chinese indicators)
        # Using a simple check for common Russian/Chinese pattern or manually added brackets
        if '(' in original_name or any('\u4e00' <= char <= '\u9fff' for char in original_name):
            continue
            
        try:
            translated = translator.translate(original_name)
            new_name = f"{original_name} ({translated})"
            
            # Update DB
            sb.table("categories").update({"category_name": new_name}).eq("category_id", leaf['category_id']).execute()
            
            count += 1
            if count % 10 == 0:
                print(f"Translated {count} categories... Last: {new_name}")
                
            # Small sleep to be nice to the API
            await asyncio.sleep(0.1)
            
        except Exception as e:
            print(f"Failed to translate {original_name}: {e}")
            
    print(f"Finished! Translated {count} categories to bilingual format.")

if __name__ == "__main__":
    asyncio.run(translate_categories())
