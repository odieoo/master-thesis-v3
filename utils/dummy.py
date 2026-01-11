#!pip install -q transformers
from transformers import pipeline
# Load sentiment-analysis pipeline
pipe = pipeline("sentiment-analysis")

# Run the model
result = pipe("I love transformers!")
print("Result:", result)

#######
assets_path = "/content/drive/MyDrive/migration"
filename = "columns.json"
# Load the file from assets
json_path = os.path.join(assets_path, filename)

with open(json_path, "r") as f:
    data = json.load(f)

# Apply transformation: replace '.' with ' '
transformed = [item.replace(".", " ") for item in data]

# Print results
print("Transformed Data:")
for line in transformed:
    print(line)
##############
print("ss", transformed)
for line in transformed:
    result = pipe(line)
    print("Result:", result)
