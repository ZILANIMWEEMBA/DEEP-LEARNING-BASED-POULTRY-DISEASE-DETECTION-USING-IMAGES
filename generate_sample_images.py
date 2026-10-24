#!/usr/bin/env python3
"""
Generate sample images for testing/demonstration.
Creates 20 synthetic images per disease class.
Images are simple colored squares with variations - NOT real medical images.
"""
import argparse
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
import random

# Define class properties (color, pattern)
CLASS_PROPERTIES = {
    "Healthy": {"color": (50, 200, 50), "name": "Healthy Poultry"},
    "Coccidiosis": {"color": (200, 100, 50), "name": "Coccidiosis"},
    "Newcastle_Disease": {"color": (200, 50, 50), "name": "Newcastle Disease"},
    "Salmonella": {"color": (150, 100, 200), "name": "Salmonella"},
}

def generate_sample_image(class_name: str, seed: int, size: tuple = (224, 224)) -> Image.Image:
    """Generate a sample image for a disease class."""
    random.seed(seed)
    np.random.seed(seed)
    
    # Create base image with class color
    base_color = CLASS_PROPERTIES[class_name]["color"]
    
    # Create array with base color
    img_array = np.ones((size[0], size[1], 3), dtype=np.uint8)
    img_array[:, :] = base_color
    
    # Add some noise/variation
    noise = np.random.normal(0, 20, (size[0], size[1], 3))
    img_array = np.clip(img_array + noise, 0, 255).astype(np.uint8)
    
    # Add some shapes for visual variety
    img = Image.fromarray(img_array)
    draw = ImageDraw.Draw(img)
    
    # Add random circles/shapes
    for _ in range(5):
        x = random.randint(20, size[0] - 20)
        y = random.randint(20, size[1] - 20)
        radius = random.randint(10, 40)
        circle_color = (
            max(0, base_color[0] + random.randint(-50, 50)),
            max(0, base_color[1] + random.randint(-50, 50)),
            max(0, base_color[2] + random.randint(-50, 50)),
        )
        draw.ellipse(
            [(x - radius, y - radius), (x + radius, y + radius)],
            fill=circle_color,
            outline=circle_color
        )
    
    # Add text label
    draw.text((10, 10), CLASS_PROPERTIES[class_name]["name"], fill=(255, 255, 255))
    
    return img

def main():
    parser = argparse.ArgumentParser(description="Generate sample images for disease detection")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("dataset/raw"),
        help="Output directory for dataset folders"
    )
    parser.add_argument(
        "--count",
        "-c",
        type=int,
        default=20,
        help="Number of images per class (default: 20)"
    )
    args = parser.parse_args()
    
    output_dir = args.output
    count = args.count
    
    print(f"Generating {count} sample images per class...")
    print(f"Output directory: {output_dir}")
    
    for class_name in CLASS_PROPERTIES.keys():
        class_dir = output_dir / class_name
        class_dir.mkdir(parents=True, exist_ok=True)
        
        for i in range(count):
            img = generate_sample_image(class_name, seed=i)
            img_path = class_dir / f"{class_name}_sample_{i:03d}.jpg"
            img.save(img_path, "JPEG", quality=85)
            print(f"  ✓ Created {img_path}")
        
        print(f"✓ Generated {count} images in {class_dir}")
    
    print("\n✓ Sample dataset ready!")
    print(f"Run: python -m machine_learning.preprocessing.preprocess --split")

if __name__ == "__main__":
    main()
