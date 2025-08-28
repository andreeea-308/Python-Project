import os
import openai

# Verificăm dacă cheia este setată
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    print("❌ Variabila de mediu 'OPENAI_API_KEY' nu este setată!")
    print("Seteaz-o cu una din metodele: .env, Environment Variables sau PowerShell permanent.")
    exit(1)

openai.api_key = api_key

# Test: trimitem un prompt simplu
try:
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": "Spune-mi un fun fact despre OpenAI"}
        ]
    )

    print("✅ Răspuns primit cu succes:\n")
    print(response['choices'][0]['message']['content'])

except Exception as e:
    print("❌ A apărut o eroare când am încercat să folosim cheia:")
    print(str(e))