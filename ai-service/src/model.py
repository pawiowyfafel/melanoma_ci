import torch.nn as nn
from torchvision import models

def get_model(num_classes=2, unfreeze_layers=1):
    model = models.resnet50(weights='DEFAULT')

    # Zamroź całą sieć
    for param in model.parameters():
        param.requires_grad = False

    # Odmroź ostatnie N bloków layer4
    if unfreeze_layers >= 1:
        for param in model.layer4.parameters():
            param.requires_grad = True
    if unfreeze_layers >= 2:
        for param in model.layer3.parameters():
            param.requires_grad = True

    # Nowa głowica klasyfikacyjna z dropoutem
    num_ftrs = model.fc.in_features
    model.fc = nn.Sequential(
        nn.Dropout(p=0.4),
        nn.Linear(num_ftrs, num_classes)
    )
    return model