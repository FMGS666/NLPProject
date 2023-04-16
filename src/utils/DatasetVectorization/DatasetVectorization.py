from ..Preprocessing.Preprocessing import *

from transformers import BertModel, AutoTokenizer
from torch.utils.data import Dataset

import torch

try:
    from optimum.bettertransformer import BetterTransformer
except ModuleNotFoundError:
    print("WARNING (ModuleError): no module named 'optimum'")


class VectorizedDataset(Dataset):
    def __init__(
            self,
            file_name: str,
            preprocesser: object = DataProcesser,
            bert_tokenization: bool = False,
            bert_tokenizer: object = AutoTokenizer, 
            pretrained_encoder: str = "bert-base-uncased",
            sentence_field: str = "concatenated_sentence",
            polarity_field: str = "polarity",
            encoder: object = BertModel
        ) -> None:
        self.file_name = file_name
        self.preprocesser = preprocesser(file_name)
        self.bert_tokenization = bert_tokenization
        self.pretrained_encoder = pretrained_encoder
        self.sentence_field = sentence_field
        self.polarity_field = polarity_field
        self.encoder = encoder.from_pretrained(self.pretrained_encoder)
        if not self.bert_tokenization:
            self.preprocesser.fit()
        else: 
            self.bert_tokenizer = bert_tokenizer.from_pretrained(self.pretrained_encoder)
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.tokenized_sentences = self.preprocesser.data_frame[self.sentence_field]
        self.polarities = self.preprocesser.data_frame[self.polarity_field]
        if torch.cuda.is_available():
            self.encoder = BetterTransformer.transorm(self.encoder, keep_original_model = True)

    def __to_torch_tensor(
            self, 
            values: list[float] | int,
            target_type: object = torch.int64
        ) -> torch.Tensor:
        return torch.Tensor([values]).to(target_type).to(self.device)

    def __create_encoder_input(
            self, 
            sentence_tensor: torch.Tensor,
            target_type: object = torch.int64
        ) -> torch.Tensor:
        token_type_ids = torch.zeros_like(sentence_tensor).to(target_type).to(self.device)
        attention_mask = torch.ones_like(sentence_tensor).to(target_type).to(self.device)
        encoder_input_dictionary = {
            "input_ids": sentence_tensor, 
            "token_type_ids": token_type_ids, 
            "attention_mask": attention_mask
        } 
        return encoder_input_dictionary

    def __encode(
            self, 
            sentence: torch.Tensor | str, 
            target_type: object = torch.int64
        ) -> torch.Tensor:
        if not self.bert_tokenization:
            encoder_input = self.__create_encoder_input(
                sentence, 
                target_type = target_type
            )
        else:
            encoder_input = self.bert_tokenizer(sentence, return_tensors="pt")
        encoded_sentence = self.encoder(**encoder_input)
        return encoded_sentence.last_hidden_state

    def __len__(
            self
        ) -> None:
        return len(self.X)

    def __getitem__(
            self, 
            idx: int
        ) -> tuple[torch.Tensor]:
        sentence = self.tokenized_sentences.iloc[idx]
        if not self.bert_tokenization:
            sentence = self.__to_torch_tensor(sentence)
        polarity = self.polarities.iloc[idx]
        sentence = self.__encode(sentence)
        polarity_tensor = self.__to_torch_tensor(polarity)
        return sentence, polarity_tensor