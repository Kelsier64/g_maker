# from PIL import Image
# import os
# import sys

# def resize_and_crop_image(input_path, output_path=None):
#     """
#     Resize JPG image to 480p and crop 4 pixels from each edge
#     """
#     try:
#         # Open the image
#         with Image.open(input_path) as img:
#             # Convert to RGB if necessary (for JPG compatibility)
#             if img.mode != 'RGB':
#                 img = img.convert('RGB')
            
#             # Resize to 480p (854x480 for 16:9 aspect ratio)
#             # You can adjust these dimensions based on your needs
#             target_width, target_height = 854, 480
#             img_resized = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
            
#             # Crop 4 pixels from each edge
#             left, top, right, bottom = 4, 4, target_width - 4, target_height - 4
#             img_cropped = img_resized.crop((left, top, right, bottom))
            
#             # Determine output path
#             if output_path is None:
#                 name, ext = os.path.splitext(input_path)
#                 output_path = f"{name}_480p_cropped{ext}"
            
#             # Save the processed image
#             img_cropped.save(output_path, 'JPEG', quality=95)
#             print(f"Processed: {input_path} -> {output_path}")
            
#     except Exception as e:
#         print(f"Error processing {input_path}: {str(e)}")

# def main():
#     if len(sys.argv) < 2:
#         print("Usage: python resize.py <image_path> [output_path]")
#         print("Example: python resize.py image.jpg")
#         return
    
#     input_path = sys.argv[1]
#     output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
#     if not os.path.exists(input_path):
#         print(f"Error: File {input_path} not found")
#         return
    
#     resize_and_crop_image(input_path, output_path)

# if __name__ == "__main__":
#     main()
