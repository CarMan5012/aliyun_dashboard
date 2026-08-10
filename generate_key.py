from cryptography.fernet import Fernet

def main():
    key = Fernet.generate_key()
    print("Generated ASSETVISTA_MASTER_KEY:")
    print(key.decode())
    print("\nPlease set this key as an environment variable, e.g., in your .env file:")
    print(f"ASSETVISTA_MASTER_KEY={key.decode()}")

if __name__ == "__main__":
    main()
