#!/bin/bash
# Script to export CloudWatch dashboard widgets as individual images

set -e

DASHBOARD_NAME="${1:-Demand_And_Capacity_Prod}"
ENVIRONMENT="${2:-Prod}"
OUTPUT_BASE="dashboard_exports"
OUTPUT_DIR="${OUTPUT_BASE}/${ENVIRONMENT}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REGION="${AWS_REGION:-eu-west-2}"

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo "========================================="
echo "CloudWatch Dashboard Image Export"
echo "========================================="
echo "Dashboard: $DASHBOARD_NAME"
echo "Environment: $ENVIRONMENT"
echo "Region: $REGION"
echo "Output: $OUTPUT_DIR"
echo ""

# Get dashboard definition
echo "Fetching dashboard definition..."
aws cloudwatch get-dashboard \
    --dashboard-name "$DASHBOARD_NAME" \
    --region "$REGION" \
    --output json > "${OUTPUT_DIR}/dashboard_definition_${TIMESTAMP}.json"

if [ $? -ne 0 ]; then
    echo "Error: Failed to fetch dashboard. Check dashboard name and AWS credentials."
    exit 1
fi

echo "✓ Dashboard definition saved"
echo ""

# Extract and process widgets using Python
echo "Extracting and capturing widget images..."

export TIMESTAMP
export OUTPUT_DIR
export REGION

python3 - <<'PYTHON_SCRIPT'
import json
import base64
import subprocess
import sys
import os

# Read dashboard definition
with open(f"{os.environ['OUTPUT_DIR']}/dashboard_definition_{os.environ['TIMESTAMP']}.json") as f:
    dashboard_data = json.load(f)

# Parse the dashboard body
dashboard_body = json.loads(dashboard_data['DashboardBody'])
widgets = dashboard_body.get('widgets', [])

print(f"Found {len(widgets)} widgets in dashboard\n")

output_dir = os.environ['OUTPUT_DIR']
region = os.environ['REGION']

for idx, widget in enumerate(widgets, 1):
    properties = widget.get('properties', {})

    # Get widget title for filename
    title = properties.get('title', f'widget_{idx}')
    safe_title = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in title)

    # Create metric widget JSON for API call
    metric_widget = {
        'width': widget.get('width', 6) * 100,
        'height': widget.get('height', 6) * 100,
    }

    # Copy relevant properties
    for key in ['metrics', 'view', 'stacked', 'region', 'title', 'period', 'stat', 'yAxis', 'annotations']:
        if key in properties:
            metric_widget[key] = properties[key]

    # Set region if not in widget
    if 'region' not in metric_widget:
        metric_widget['region'] = region

    # Override time range to show last 8 weeks (56 days)
    from datetime import datetime, timedelta
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(weeks=8)

    metric_widget['start'] = start_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    metric_widget['end'] = end_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')

    widget_json = json.dumps(metric_widget)
    output_file = f"{output_dir}/{idx:02d}_{safe_title}.png"

    print(f"[{idx}/{len(widgets)}] Capturing: {title}")

    try:
        # Call AWS CLI to get widget image
        result = subprocess.run(
            [
                'aws', 'cloudwatch', 'get-metric-widget-image',
                '--metric-widget', widget_json,
                '--output-format', 'png',
                '--region', region,
                '--output', 'text'
            ],
            capture_output=True,
            text=True,
            check=True
        )

        # Decode base64 and save
        image_data = base64.b64decode(result.stdout)
        with open(output_file, 'wb') as f:
            f.write(image_data)

        print(f"    ✓ Saved to: {output_file}")

    except subprocess.CalledProcessError as e:
        print(f"    ✗ Failed: {e.stderr}")
    except Exception as e:
        print(f"    ✗ Error: {str(e)}")

    print()

print("========================================")
print("Export complete!")
print(f"Images saved to: {output_dir}/")
print("========================================")

PYTHON_SCRIPT

echo ""
echo "✓ Export for $ENVIRONMENT complete!"
