import os
import sys
from PIL import Image

def compress_images():
    here = os.path.dirname(os.path.abspath(__file__))
    files = ["p1s1.png", "p1s2.png", "p1s3.png", "p1s4.png", "p1s5.png", "p1s6.png", "p2.png", "p3.png"]
    
    print(f"Compressing {len(files)} PNG images to JPG without cropping...")
    
    for filename in files:
        png_path = os.path.join(here, filename)
        if not os.path.exists(png_path):
            print(f"Warning: {filename} not found at {png_path}")
            continue
            
        jpg_filename = os.path.splitext(filename)[0] + ".jpg"
        jpg_path = os.path.join(here, jpg_filename)
        
        orig_size = os.path.getsize(png_path)
        
        with Image.open(png_path) as img:
            # Check size / dimensions
            width, height = img.size
            
            # Handle alpha channel if present
            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                bg = Image.new("RGB", img.size, (10, 12, 11)) # #0A0C0B
                if img.mode == "RGBA":
                    bg.paste(img, mask=img.split()[3])
                else:
                    bg.paste(img.convert("RGBA"), mask=img.convert("RGBA").split()[3])
                rgb_img = bg
            else:
                rgb_img = img.convert("RGB")
                
            rgb_img.save(jpg_path, "JPEG", quality=95, optimize=True)
            
        new_size = os.path.getsize(jpg_path)
        reduction = (1 - new_size / orig_size) * 100
        print(f"Compressed {filename} ({width}x{height}, {orig_size/1024:.1f} KB) -> {jpg_filename} ({new_size/1024:.1f} KB, -{reduction:.1f}%)")

if __name__ == "__main__":
    compress_images()
