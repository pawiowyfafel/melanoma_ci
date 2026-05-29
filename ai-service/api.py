from fastapi import FastAPI, File, UploadFile
import torch
import io
from PIL import Image
from torchvision import transforms
from src.model import get_model 

app = FastAPI()
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def load_trained_model(model_path="model_gita.pth"):
    # 1. Wczytaj checkpoint
    checkpoint = torch.load(model_path, map_location=device)
    config = checkpoint["config"]
    
    print(f"Wczytuję model: {config['model_name']} (unfreeze: {config['unfreeze_layers']})")

    model = get_model(
        num_classes=2, 
        unfreeze_layers=config["unfreeze_layers"]
    ).to(device)
    
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    return model, config

model, model_config = load_trained_model()

preprocess = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    contents = await file.read()
    image = Image.open(io.BytesIO(contents)).convert("RGB")
    tensor = preprocess(image).unsqueeze(0).to(device)
    
    with torch.no_grad():
        outputs = model(tensor)
        probabilities = torch.nn.functional.softmax(outputs[0], dim=0)
        confidence, predicted_class = torch.max(probabilities, 0)

    class_names = ["benign", "malignant"]
    
    return {
        "prediction": class_names[predicted_class.item()],
        "confidence": float(confidence.item()),
        "model_used": model_config["model_name"]
    }