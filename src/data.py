import software

def generate_astronaut() -> software.Astronaut:
    astronaut = software.Astronaut(
        "Alex Morgan",
        34,
        65,
        98,
        36.7,
        (115, 75),
        14
    )
    return astronaut

print(generate_astronaut().name)
