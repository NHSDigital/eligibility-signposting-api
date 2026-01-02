#!/usr/bin/env python3
"""
Generate an HTML report from exported dashboard images
"""
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
        return None

    # Default output filename
    if output_file is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'{base_dir}/dashboard_report_{timestamp}.html'

    dashboard_name = "Monthly Demand And Capacity Report - EliD"
    report_date = datetime.now().strftime('%d %B %Y at %H:%M')

    # Build HTML
    # Read CSS from file to embed in HTML
    css_path = Path(__file__).parent / "dashboard_report.css"
    try:
        with open(css_path, "r", encoding="utf-8") as css_file:
            css_content = css_file.read()
    except Exception as e:
        print(f"[ERROR] Could not read CSS file: {e}")
        css_content = ""

    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NHS Dashboard Report - {dashboard_name}</title>
    <style>
{css_content}
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
'''

    # ---------------------------------------------------------
    # Section 1: Production
    # ---------------------------------------------------------
    html_content += """
        <div class=\"section-header\">
            <h2>Production Environment</h2>
        </div>
    """
    html_content += generate_section_html("Prod", base_path / "Prod")

    # ---------------------------------------------------------
    # Section 2: Preprod Environments
    # ---------------------------------------------------------
    html_content += """
        <div class=\"section-header\" style=\"margin-top: 48px;\">
            <h2>Preprod Environments</h2>
        </div>
    """

    # Order: Preprod, Test, Dev
    for env in ["Preprod", "Test", "Dev"]:
        html_content += generate_section_html(env, base_path / env)

    # Close HTML
    html_content += """
    </div>

    <footer class=\"footer\">
        <div class=\"nhs-container\">
            <p>Eligibility Data Product • Generated from AWS CloudWatch</p>
        </div>
    </footer>
</body>
</html>
"""

    # Print output path for debugging
    print(f"[DEBUG] Output HTML file will be written to: {output_file}")
    # Ensure output directory exists
    output_dir = Path(output_file).parent
    if not output_dir.exists():
        print(f"[DEBUG] Creating output directory: {output_dir}")
        output_dir.mkdir(parents=True, exist_ok=True)

    # Write HTML file with error handling
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"[DEBUG] Successfully wrote report to {output_file}")
    except Exception as e:
        print(f"[ERROR] Failed to write report: {e}")

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

# Only run this block if the script is executed directly
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Generate HTML report from dashboard images')
    parser.add_argument('--input', default='dashboard_exports',
                        help='Directory containing dashboard images')
    parser.add_argument('--output', help='Output HTML file path')

    args = parser.parse_args()

    generate_html_report(args.input, args.output)
