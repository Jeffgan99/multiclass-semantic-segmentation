# influenced by:  
# https://github.com/qubvel/ttach

import torch
from torch import nn

def hflip(x):
    """flip batch of images horizontally"""
    return x.flip(1)

def vflip(x):
    """flip batch of images vertically"""
    return x.flip(2)

def transform(x):
    """
    input: 3D tensor
    output: 4D tensor: 
        [orig, hflip, vflip, hflip->vflip]
    """
    output = [x]
    _x = hflip(x)
    output.append(_x)
    _x = vflip(_x)
    x = vflip(x)
    output.extend([x, _x])
    return torch.cat([el.unsqueeze(0) for el in output])
    
def inv_transform(x):
    """
    input: 4D tensor
    output: 4D tensor
    inverse transform: 
        [orig, hflip, vflip, vflip->hflip]
    """
    x[1] = hflip(x[1])
    x[2] = vflip(x[2])
    x[3] = vflip(hflip(x[3]))
    return x
    
    
class TTAWrapper(nn.Module):
    
    def __init__(self, model, merge_mode="mean", activate=False, temperature=0.5):
        super().__init__()
        self.model = model
        self.activate = activate
        self.temperature = temperature
        self.merge_mode = merge_mode

        if self.merge_mode not in ['mean', 'tsharpen']:
            raise ValueError('Merge type is not correct: `{}`.'.format(self.merge_mode))
    
    def forward(self, images):
        result = []
        batch_size = images.size(0)
        for image in images:
            augmented = transform(image)
            aug_prediction = self.model(augmented)
            if self.activate:
                aug_prediction = torch.sigmoid(aug_prediction)
            aug_prediction = inv_transform(aug_prediction)
            
            if self.merge_mode == "mean":
                result.append(aug_prediction.sum(0))
            elif self.merge_mode == "tsharpen":
                # drop negatives to prevent NaNs
                aug_prediction[aug_prediction < 0] = 0
                result.append(torch.pow(aug_prediction[0], self.temperature))
                for pred in aug_prediction[1:]:
                    result[-1] += torch.pow(pred, self.temperature)
            result[-1] = (result[-1] / batch_size).unsqueeze(0)

        return torch.cat(result)
