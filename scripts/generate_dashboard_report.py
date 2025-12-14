#!/usr/bin/env python3
"""
Generate an HTML report from exported dashboard images
"""
import os
import base64
from datetime import datetime
from pathlib import Path

# Context definitions for widgets
WIDGET_CONTEXT = {
    "DynamoDB": "Shows the consumed write capacity units for the DynamoDB table. High usage may indicate need for scaling.",
    "Lambda": "Number of times the Lambda function was invoked. Spikes may indicate increased traffic or retries.",
    "5xx": "Server-side errors. Should be zero ideally.",
    "4xx": "Client-side errors. Frequent 4xx errors might indicate issues with client requests.",
    "Latency": "Response time of the service. Lower is better.",
    "CPU": "CPU utilization percentage. Consistently high CPU might require instance upsizing.",
    "Memory": "Memory usage. Ensure there is sufficient headroom.",
    "Errors": "Count of error events.",
    "Throttles": "Number of throttled requests. Indicates capacity limits are being hit."
}

def get_widget_description(title):
    """
    Get a description for a widget based on keywords in its title.
    """
    title_lower = title.lower()
    description_parts = []

    for key, desc in WIDGET_CONTEXT.items():
        if key.lower() in title_lower:
            description_parts.append(desc)

    if not description_parts:
        return "Performance metric visualization."

    return " ".join(description_parts)

def generate_section_html(env_name, images_dir):
    """
    Generate HTML for a specific environment section.
    """
    images_path = Path(images_dir)
    if not images_path.exists():
        return f"<p>No data found for {env_name}</p>"

    image_files = sorted(images_path.glob('*.png'))
    if not image_files:
        return f"<p>No images found for {env_name}</p>"

    html = f"""
    <div class="env-section">
        <h2 class="env-title">{env_name}</h2>
    """

    for idx, image_file in enumerate(image_files, 1):
        filename = image_file.stem
        title = filename.split('_', 1)[1] if '_' in filename else filename
        title = title.replace('_', ' ')
        description = get_widget_description(title)

        with open(image_file, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')

        html += f"""
        <div class="widget-card">
            <div class="widget-header">
                <div class="widget-title">{idx}. {title}</div>
                <div class="widget-description">{description}</div>
            </div>
            <div class="widget-image-container">
                <img class="widget-image"
                    src="data:image/png;base64,{image_data}"
                    alt="{title}">
            </div>
        </div>
        """

    html += "</div>"
    return html

def generate_html_report(base_dir='dashboard_exports', output_file=None):
    """
    Generate an HTML report with all dashboard widget images from multiple environments.
    """
    base_path = Path(base_dir)

    if not base_path.exists():
        print(f"Error: Base directory {base_dir} not found")
        return None

    # Default output filename
    if output_file is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'{base_dir}/dashboard_report_{timestamp}.html'

    # Get dashboard name and timestamp from definition file
    dashboard_name = "Monthly Demand And Capacity Report - EliD"
    report_date = datetime.now().strftime('%d %B %Y at %H:%M')

    # Build HTML
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NHS Dashboard Report - {dashboard_name}</title>
    <style>
        :root {{
            --nhs-blue: #005EB8;
            --nhs-white: #FFFFFF;
            --nhs-black: #231f20;
            --nhs-dark-grey: #425563;
            --nhs-mid-grey: #768692;
            --nhs-pale-grey: #E8EDEE;
            --nhs-warm-yellow: #FFB81C;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: "Frutiger W01", Arial, sans-serif;
            background: var(--nhs-pale-grey);
            color: var(--nhs-black);
            line-height: 1.5;
        }}

        .nhs-header {{
            background-color: var(--nhs-blue);
            color: var(--nhs-white);
            padding: 24px 0;
            margin-bottom: 32px;
        }}

        .nhs-container {{
            max-width: 960px;
            margin: 0 auto;
            padding: 0 16px;
        }}

        .nhs-logo {{
            font-weight: 700;
            font-size: 24px;
            letter-spacing: -0.5px;
            display: inline-block;
            margin-right: 16px;
            padding-right: 16px;
            border-right: 1px solid rgba(255, 255, 255, 0.3);
        }}

        .report-title {{
            font-size: 24px;
            font-weight: 600;
            display: inline-block;
        }}

        .report-meta {{
            margin-top: 8px;
            font-size: 14px;
            opacity: 0.9;
        }}

        .content {{
            padding-bottom: 48px;
        }}

        .section-header {{
            background: var(--nhs-white);
            padding: 16px 24px;
            margin-bottom: 24px;
            border-left: 8px solid var(--nhs-blue);
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}

        .section-header h2 {{
            font-size: 24px;
            color: var(--nhs-blue);
            margin: 0;
        }}

        .env-section {{
            margin-bottom: 48px;
        }}

        .env-title {{
            font-size: 20px;
            color: var(--nhs-dark-grey);
            margin-bottom: 20px;
            padding-bottom: 8px;
            border-bottom: 2px solid #d8dde0;
        }}

        .widget-card {{
            background: var(--nhs-white);
            border: 1px solid #d8dde0;
            border-bottom: 4px solid var(--nhs-blue);
            margin-bottom: 32px;
            padding: 24px;
            page-break-inside: avoid;
        }}

        .widget-header {{
            margin-bottom: 16px;
            border-bottom: 1px solid var(--nhs-pale-grey);
            padding-bottom: 16px;
        }}

        .widget-title {{
            font-size: 19px;
            font-weight: 600;
            color: var(--nhs-black);
            margin-bottom: 8px;
        }}

        .widget-description {{
            font-size: 16px;
            color: var(--nhs-dark-grey);
            background: #f0f4f5;
            padding: 12px;
            border-left: 4px solid var(--nhs-mid-grey);
        }}

        .widget-image-container {{
            margin-top: 20px;
            text-align: center;
        }}

        .widget-image {{
            max-width: 100%;
            height: auto;
            border: 1px solid var(--nhs-pale-grey);
        }}

        .footer {{
            text-align: center;
            padding: 32px 0;
            color: var(--nhs-mid-grey);
            font-size: 14px;
            border-top: 1px solid #d8dde0;
            margin-top: 48px;
        }}

        @media print {{
            body {{
                background: white;
            }}
            .nhs-header {{
                background: white;
                color: black;
                border-bottom: 2px solid var(--nhs-blue);
            }}
            .widget-card {{
                border: none;
                border-bottom: 1px solid #ccc;
            }}
            .section-header {{
                border: none;
                padding: 0;
                margin-bottom: 16px;
            }}
        }}
    </style>
</head>
<body>
    <header class="nhs-header">
        <div class="nhs-container">
            <div class="header-content">
                <span class="nhs-logo">NHS</span>
                <h1 class="report-title">{dashboard_name}</h1>
                <div class="report-meta">Generated on {report_date}</div>
            </div>
        </div>
    </header>

    <div class="nhs-container content">
"""

    # ---------------------------------------------------------
    # Section 1: Production
    # ---------------------------------------------------------
    html_content += """
        <div class="section-header">
            <h2>Production Environment</h2>
        </div>
    """
    html_content += generate_section_html("Prod", base_path / "Prod")

    # ---------------------------------------------------------
    # Section 2: Preprod Environments
    # ---------------------------------------------------------
    html_content += """
        <div class="section-header" style="margin-top: 48px;">
            <h2>Preprod Environments</h2>
        </div>
    """

    # Order: Preprod, Test, Dev
    for env in ["Preprod", "Test", "Dev"]:
        html_content += generate_section_html(env, base_path / env)

    # Close HTML
    html_content += """
    </div>

    <footer class="footer">
        <div class="nhs-container">
            <p>Eligibility Data Product • Generated from AWS CloudWatch</p>
        </div>
    </footer>
</body>
</html>
"""

    # Write HTML file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"\n✓ Capacity and Demand Report generated: {output_file}")
    print(f"\nTo view:")
    print(f"  - Open in browser: file://{Path(output_file).absolute()}")
    print(f"  - Or run: xdg-open {output_file}")

    return output_file

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Generate HTML report from dashboard images')
    parser.add_argument('--input', default='dashboard_exports',
                        help='Directory containing dashboard images')
    parser.add_argument('--output', help='Output HTML file path')

    args = parser.parse_args()

    generate_html_report(args.input, args.output)
