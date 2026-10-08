from PIL import Image, ImageDraw

def mask_aadhaar_image(file_path, bounding_box):
    """
    Masks the first 8 digits of an Aadhaar number on the image.
    bounding_box is [ [x1,y1], [x2,y2], [x3,y3], [x4,y4] ] from RapidOCR.
    """
    try:
        img = Image.open(file_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
            
        draw = ImageDraw.Draw(img)
        
        # Calculate bounding box of the whole 12 digit string
        xs = [pt[0] for pt in bounding_box]
        ys = [pt[1] for pt in bounding_box]
        
        xmin, xmax = min(xs), max(xs)
        ymin, ymax = min(ys), max(ys)
        
        # The first 8 digits take up roughly 2/3 (66%) of the width
        # Or more accurately, 8/14 of the string if counting spaces, ~60-70%
        # We will mask the first 75% of the width to be safe.
        mask_xmax = xmin + (xmax - xmin) * 0.75
        
        # Draw a solid black rectangle over the first 8 digits
        draw.rectangle([xmin, ymin, mask_xmax, ymax], fill="black")
        
        # Overwrite original image
        img.save(file_path)
        return True
    except Exception as e:
        print(f"Failed to mask Aadhaar: {e}")
        return False
