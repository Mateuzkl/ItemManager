"""Test script for assets_editor module"""
import sys
sys.path.insert(0, 'data')

try:
    from assets_editor import AssetsEditorTab, AppearancesParser, LZMAHandler, CatalogEntry, AppearanceData
    print("SUCCESS: All modules imported correctly")
    print("  - AssetsEditorTab")
    print("  - AppearancesParser")
    print("  - LZMAHandler")
    print("  - CatalogEntry")
    print("  - AppearanceData")
    
    # Test parser instantiation
    parser = AppearancesParser()
    print("\nAppearancesParser instantiated OK")
    
    # Test LZMA handler
    print("LZMAHandler available OK")
    
    print("\n✓ All tests passed!")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
