from cryptography.fernet import Fernet

def test_fernet_key(fernet_key, data):
    fernet = Fernet(fernet_key)
    encrypted = fernet.encrypt(data.encode())
    print(f"Encrypted: {encrypted}")
    decrypted = fernet.decrypt(encrypted).decode()
    print(f"Decrypted: {decrypted}")

if __name__ == "__main__":
    # Replace with your actual Fernet key
    fernet_key = b'your_fernet_key_here'
    data = 'test_data'
    
    try:
        test_fernet_key(fernet_key, data)
    except Exception as e:
        print(f"Error: {e}")
