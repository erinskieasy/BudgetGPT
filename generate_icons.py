
from PIL import Image, ImageDraw

def generate_pwa_icon(size):
    # Create a new image with a white background
    image = Image.new('RGB', (size, size), 'white')
    draw = ImageDraw.Draw(image)
    
    # Draw a simple icon (a filled circle with a border)
    padding = size // 8
    draw.ellipse([padding, padding, size - padding, size - padding], 
                 fill='#4CAF50', outline='#2E7D32', width=size//32)
    
    return image

# Generate icons in required sizes
sizes = [192, 512]
for size in sizes:
    icon = generate_pwa_icon(size)
    icon.save(f'generated-icon-{size}.png')
