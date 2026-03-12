import uuid
import random
import torchvision
import numpy as np
import torchvision.transforms as transforms

reviews = [
    "Excellent value for money.", "The best purchase I've made this year.", 
    "Super fast shipping!", "Exceeded all my expectations.", 
    "High quality materials.", "Very easy to use.", 
    "Works like a charm.", "Highly recommended for everyone.", 
    "Truly a premium experience.", "I love the sleek design.", 
    "Five stars, no doubt.", "Great customer service.", 
    "Exactly what I was looking for.", "Perfect for daily use.", 
    "Surprisingly good performance.", "Very comfortable and durable.", 
    "A life-changing product.", "Beautifully packaged.", 
    "Simple yet effective.", "Incredible attention to detail.", 
    "My family loves it.", "Fast and reliable.", 
    "Everything works as described.", "A total bargain!", 
    "Top-notch build quality.", "I will buy this again.", 
    "Absolutely brilliant idea.", "Very intuitive interface.", 
    "The color is even better in person.", "Smooth and quiet operation.", 
    "Lightweight and portable.", "Solid construction.", 
    "Very impressed with the battery life.", "Makes my life so much easier.",
    "Waste of money.", "It broke after two days.", 
    "Terrible build quality.", "The instructions were very confusing.", 
    "Does not look like the pictures.", "I want a refund immediately.", 
    "Extremely noisy and annoying.", "Very poor customer support.", 
    "It arrived damaged.", "Not compatible as advertised.", 
    "Complete disappointment.", "Cheap plastic feel.", 
    "The app keeps crashing.", "Way overpriced for what it is.", 
    "I regret buying this.", "It smells like chemicals.", 
    "Very difficult to set up.", "The screen is too dim.", 
    "Stopped working after a week.", "Much smaller than expected.", 
    "Low quality for the price.", "Horrible shipping experience.", 
    "It feels very flimsy.", "The battery doesn't hold a charge.", 
    "I would not recommend this to anyone.", "Very slow performance.", 
    "Customer service ignored my emails.", "Not what I ordered at all.", 
    "It’s a total scam.", "Missing several parts.", 
    "Uncomfortable to use for long periods.", "Very outdated technology.", 
    "The box was completely crushed.",
    "It’s okay for the price.", "Does the job, nothing special.", 
    "Average quality overall.", "It arrived on time.", 
    "Decent, but could be better.", "Works as expected, I guess.", 
    "Neither good nor bad.", "Just a standard product.", 
    "It is what it is.", "Satisfactory performance.", 
    "Not great, but not terrible.", "Fairly simple to operate.", 
    "It’s fine for basic needs.", "Okay, but I’ve seen better.", 
    "Some features are missing.", "Mixed feelings about this purchase.", 
    "Shipping was okay, product is fine.", "Moderate build quality.", 
    "It’s a bit basic.", "Not the best, but it works.", 
    "Functional, but boring design.", "Meets the bare minimum requirements.", 
    "Mediocre experience overall.", "It serves its purpose.", 
    "Average shipping speed.", "Acceptable for a one-time use.", 
    "Nothing to write home about.", "It’s a generic version.", 
    "Ordinary product, ordinary results.", "Standard features included.", 
    "Average battery life.", "The size is standard.", 
    "It’s an alright alternative."
]
transform = transforms.Compose([transforms.ToTensor()])
cifar_data = torchvision.datasets.CIFAR100(root='./data', train=True, download=True)

def generate_task_event():
    task_type = random.choice(["text_analysis", "image_classification"])

    if task_type == "text_analysis":
        routing_key = 'ruta_texto'
        content = random.choice(reviews)
    else:
        idx = random.randint(0, len(cifar_data) - 1)
        # Obtenemos la imagen real del dataset (es un objeto PIL o Tensor)
        image, label = cifar_data[idx] 
        
        # Convertimos la imagen a una lista de Python para que sea serializable en JSON
        # CIFAR-100 son imágenes de 32x32x3
        content = np.array(image).tolist() 
        
        routing_key = 'ruta_imagen'

    return {
        "task_id": str(uuid.uuid4())[:8], 
        "type": task_type,
        "content": content,
        "routing_key": routing_key
    }