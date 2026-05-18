"""
PyTorch LSTM Architecture — MoistureLSTM
Trained on dataset_lstm_training.json
Input: (batch, seq_len=12, features=5)
Output: (batch, 3)  → [moisture_1h, moisture_6h, moisture_24h]
"""
import torch
import torch.nn as nn


class MoistureLSTM(nn.Module):
    def __init__(self, input_size=5, hidden_size=128, num_layers=2, output_size=3, dropout=0.2):
        super(MoistureLSTM, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout,
        )
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 64),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(64, output_size),
        )

    def forward(self, x):
        # x: (batch, seq, features)
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)
        out, _ = self.lstm(x, (h0, c0))
        out = self.fc(out[:, -1, :])   # last time step
        return out
