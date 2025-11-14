from transformers import MarianMTModel, MarianTokenizer


class KoreanEnglishTranslator:
    def __init__(self, model_name: str = "Helsinki-NLP/opus-mt-ko-en") -> None:
        self.tokenizer = MarianTokenizer.from_pretrained(model_name)
        self.model = MarianMTModel.from_pretrained(model_name)

    def translate(self, text: str) -> str:
        encoded = self.tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True,
        )
        translated = self.model.generate(**encoded)
        return self.tokenizer.decode(translated[0], skip_special_tokens=True)


if __name__ == "__main__":
    translator = KoreanEnglishTranslator()
    print(translator.translate("Middle-aged or old-aged men's documentary movie"))