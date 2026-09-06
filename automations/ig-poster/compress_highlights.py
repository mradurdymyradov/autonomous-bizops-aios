import os
import sys

try:
    from PIL import Image
except ImportError:
    import subprocess
    print("Pillow not found, installing it...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
        from PIL import Image
    except Exception as e:
        print(f"Failed to install Pillow: {e}")
        sys.exit(1)

def compress_png_to_jpeg(source_dir):
    if not os.path.exists(source_dir):
        print(f"Source directory {source_dir} does not exist.")
        return
    
    files = [f for f in os.listdir(source_dir) if f.lower().endswith('.png')]
    if not files:
        print("No PNG files found to compress.")
        return
        
    print(f"Found {len(files)} PNG files to compress...")
    for f in files:
        png_path = os.path.join(source_dir, f)
        jpg_name = os.path.splitext(f)[0] + '.jpg'
        jpg_path = os.path.join(source_dir, jpg_name)
        
        try:
            with Image.open(png_path) as img:
                # Brand near-black background #0A0C0B is RGB (10, 12, 11)
                bg_color = (10, 12, 11)
                
                # Check if it's a story (name starts with 'h') or a cover (starts with 'c')
                if f.lower().startswith('h'):
                    # Center crop the 1024x1024 square image horizontally to 9:16 (576x1024)
                    # Left: 224, Top: 0, Right: 800, Bottom: 1024
                    cropped = img.crop((224, 0, 800, 1024))
                    # Resize to crisp high-quality 1080x1920 Story resolution
                    background = cropped.resize((1080, 1920), Image.Resampling.LANCZOS)
                else:
                    # Keep covers square (1024x1024)
                    background = Image.new("RGB", img.size, bg_color)
                    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                        background.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else img.convert('RGBA').split()[3])
                    else:
                        background.paste(img)
                
                # Convert background to RGB before saving as JPEG
                if background.mode in ('RGBA', 'LA') or (background.mode == 'P' and 'transparency' in background.info):
                    background = background.convert('RGB')
                
                background.save(jpg_path, "JPEG", quality=95)

            print(f"Processed & Compressed: {f} -> {jpg_name}")
        except Exception as e:
            print(f"Error processing {f}: {e}")

if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    highlights_dir = os.path.join(script_dir, 'highlights')
    if not os.path.exists(highlights_dir):
        os.makedirs(highlights_dir)
        print(f"Created directory: {highlights_dir}")
    compress_png_to_jpeg(highlights_dir)
