#!/usr/bin/env python3
"""
Generate an HTML report from exported dashboard images
"""
import os
import base64
from datetime import datetime
from pathlib import Path

def generate_html_report(images_dir='dashboard_exports', output_file=None):
    """
    Generate an HTML report with all dashboard widget images.
    Images are embedded as base64 for portability.
    """

    images_path = Path(images_dir)

    if not images_path.exists():
        print(f"Error: Directory {images_dir} not found")
        return None

    # Find all PNG images
    image_files = sorted(images_path.glob('*.png'))

    if not image_files:
        print(f"Error: No PNG images found in {images_dir}")
        return None

    print(f"Found {len(image_files)} images to include in report")

    # Default output filename
    if output_file is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'{images_dir}/dashboard_report_{timestamp}.html'

    # Get dashboard name and timestamp from definition file
    dashboard_name = "Monthly Demand And Capacity Report - EliD"
    report_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Build HTML
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Report - {dashboard_name}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #f5f5f5;
            padding: 20px;
            color: #333;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}

        .header {{
            background: linear-gradient(135deg, #232F3E 0%, #FF9900 100%);
            color: white;
            padding: 30px 40px;
            border-bottom: 4px solid #FF9900;
        }}

        .header h1 {{
            font-size: 32px;
            font-weight: 600;
            margin-bottom: 10px;
        }}

        .header .subtitle {{
            font-size: 16px;
            opacity: 0.9;
        }}

        .content {{
            padding: 40px;
        }}

        .widget {{
            margin-bottom: 40px;
            page-break-inside: avoid;
        }}

        .widget-title {{
            font-size: 20px;
            font-weight: 600;
            color: #232F3E;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #FF9900;
        }}

        .widget-image {{
            width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        .footer {{
            background: #f8f8f8;
            padding: 20px 40px;
            text-align: center;
            color: #666;
            font-size: 14px;
            border-top: 1px solid #ddd;
        }}

        @media print {{
            body {{
                background: white;
                padding: 0;
            }}

            .container {{
                box-shadow: none;
            }}

            .widget {{
                page-break-inside: avoid;
            }}
        }}

        @media (max-width: 768px) {{
            body {{
                padding: 10px;
            }}

            .content {{
                padding: 20px;
            }}

            .header {{
                padding: 20px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 {dashboard_name}</h1>
            <div class="subtitle">Last 8 Weeks Report • Generated: {report_date}</div>
        </div>

        <div class="content">
"""

    # Add each widget image
    for idx, image_file in enumerate(image_files, 1):
        # Extract widget title from filename (remove number prefix and extension)
        filename = image_file.stem
        # Remove leading number and underscore (e.g., "01_")
        title = filename.split('_', 1)[1] if '_' in filename else filename
        # Replace underscores with spaces
        title = title.replace('_', ' ')

        # Read and encode image
        with open(image_file, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')

        html_content += f"""
            <div class="widget">
                <div class="widget-title">{idx}. {title}</div>
                <img class="widget-image"
                    src="data:image/png;base64,{image_data}"
                    alt="{title}">
            </div>
"""

    # Close HTML
    html_content += """
        </div>

        <div class="footer">
            Generated from AWS CloudWatch Dashboard
        </div>
    </div>
</body>
</html>
"""

    # Write HTML file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"\n✓ Report generated: {output_file}")
    print(f"\nTo view:")
    print(f"  - Open in browser: file://{Path(output_file).absolute()}")
    print(f"  - Or run: xdg-open {output_file}")
    print(f"\nTo save as PDF: Open in browser → Print → Save as PDF")

    return output_file

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Generate HTML report from dashboard images')
    parser.add_argument('--input', default='dashboard_exports',
                        help='Directory containing dashboard images')
    parser.add_argument('--output', help='Output HTML file path')

    args = parser.parse_args()

    generate_html_report(args.input, args.output)
