from main import category_model, urgency_model

tests = [
"i want refund immediately",
"your service is very bad",
"please send invoice copy",
"thank you for great support",
"lottery win click link"
]

for t in tests:
    print(t)
    print("category:", category_model.predict([t])[0])
    print("urgency:", urgency_model.predict([t])[0])
    print("------")
