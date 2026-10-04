"""Structured temporal encoder with the vendored JevLike probabilistic option scorer."""
import torch
from torch import nn
from jevlike.model import AttentionHead


class ExecutionJev(nn.Module):
    def __init__(self,features=24,steps=16,width=32):
        super().__init__()
        self.config=dict(features=features,steps=steps,width=width)
        self.project=nn.Linear(features,width)
        self.position=nn.Parameter(torch.zeros(steps,width))
        self.encoder=nn.TransformerEncoder(nn.TransformerEncoderLayer(width,4,2*width,dropout=0.,batch_first=True),1,enable_nested_tensor=False)
        self.options=nn.Parameter(torch.randn(60,width)*.02)
        self.head=AttentionHead(width,16)
        self.reconstruct=nn.Linear(width,features)
        self.mask_token=nn.Parameter(torch.zeros(features))

    def encode(self,x):
        if x.ndim!=3 or tuple(x.shape[1:])!=(self.config['steps'],self.config['features']):raise ValueError('sequence shape mismatch')
        return self.encoder(self.project(x)+self.position)

    def forward(self,x):
        encoded=self.encode(x)
        options=self.options.unsqueeze(0).expand(len(x),-1,-1)
        scores=self.head(encoded,torch.ones(x.shape[:2],dtype=torch.bool,device=x.device),options,
                         torch.ones((len(x),60),dtype=torch.bool,device=x.device))
        return scores.reshape(len(x),3,2,2,5)

    def masked_loss(self,x,mask):
        if mask.shape!=x.shape[:2] or not mask.any():raise ValueError('nonempty token mask required')
        corrupted=torch.where(mask.unsqueeze(-1),self.mask_token,x)
        predicted=self.reconstruct(self.encode(corrupted))
        return ((predicted[mask]-x[mask])**2).mean()
