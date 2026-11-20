import time
import hashlib
from pathlib import Path
import pandas as pd

from Crypto.Cipher import AES, DES3, ChaCha20
from Crypto.PublicKey import RSA,ECC
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
from Crypto.Protocol.DH import key_agreement
from Crypto.Hash import SHAKE128
file_sizes = [1024,100*1024,1024*1024,5*1024*1024, 10*1024*1024]
results_dir = Path('results')
data_dir = Path('Data')
results_dir.mkdir(exist_ok=True)
data_dir.mkdir(exist_ok=True)

def create_file(size: int) -> bytes:
    data = get_random_bytes(size)
    path = data_dir / f'test_{size}.bin'
    with open(path, "wb") as f:
        f.write(data)
    return data

def time_function(func, *args, **kwargs):
    start = time.perf_counter()
    result =  func(*args,**kwargs)
    end = time.perf_counter()
    return result, end - start

def run_hashing(data :bytes):
    results = {}
    _, t= time_function(hashlib.sha256, data)
    results["SHA-256"] = t

    _, t= time_function(hashlib.sha3_256, data)
    results["SHA3-256"] = t

    _, t= time_function(hashlib.blake2b, data)
    results["BLAKE2b"] = t

    return results

def run_symmetric(data: bytes):
    results = {}

    key = get_random_bytes(32)
    cipher = AES.new(key, AES.MODE_GCM)
    _, t_enc = time_function(cipher.encrypt_and_digest, data)
    results['AES-256-GCM'] = t_enc

    key = get_random_bytes(32)
    nonce = get_random_bytes(12)
    cipher = ChaCha20.new(key=key,nonce=nonce)
    _, t_enc = time_function(cipher.encrypt, data)
    results['ChaCha20'] = t_enc

    key=DES3.adjust_key_parity(get_random_bytes(24))
    cipher = DES3.new(key, DES3.MODE_CBC)
    padded = pad(data, DES3.block_size)
    _, t_enc = time_function(cipher.encrypt, padded)
    results['3DES'] = t_enc

    return results

def run_asymmetric():
    result = {
        'KeyGen':{},
        'Operation': {}
    }

    key,t = time_function(RSA.generate, 2048)
    result['KeyGen']["RSA-2048"] = t

    cipher = PKCS1_OAEP.new(key)
    data = get_random_bytes(190)
    _, t = time_function(cipher.encrypt,data)
    result['Operation']['RSA-2048'] = t

    key,t = time_function(RSA.generate, 4096)
    result['KeyGen']['RSA-4096'] = t

    cipher = PKCS1_OAEP.new(key)
    data = get_random_bytes(400)
    _, t = time_function(cipher.encrypt,data)
    result['Operation']['RSA-4096'] = t

    key, t = time_function(ECC.generate, curve='P-256')
    result["KeyGen"]['ECC-P256'] = t

    other_key = ECC.generate(curve='P-256')

    def do_ecdh():
        return key_agreement(
            static_priv=key,
            static_pub = other_key.public_key(),
            kdf=lambda x: SHAKE128.new(x).read(32)
        )
    _, t = time_function(do_ecdh)
    result['Operation']['ECC-P256'] = t
    return result

def main():
    all_results = []

    print('Creating test files and running encryption')

    for size in file_sizes:
        print(f'Processing {size/1024:.0f} KB file')
        data = create_file(size)

        hash_result = run_hashing(data)
        for algo,t in hash_result.items():
            all_results.append({
                "Category": "Hashing",
                "Algorithm": algo,
                "FileSize_KB": size / 1024,
                "Time_sec": t
                })

        sym_result = run_symmetric(data)
        for algo,t in sym_result.items():
            all_results.append({
                "Category": "Symmetric",
                "Algorithm": algo,
                "FileSize_KB": size / 1024,
                "Time_sec": t
            })

    print("Running asymmetric key generation")
    asym_result = run_asymmetric()
    for algo, t in asym_result["KeyGen"].items():
            all_results.append({
            "Category": "Asymmetric-KeyGen",
            "Algorithm": algo,
            "FileSize_KB": 0,
            "Time_sec": t
        })

    for algo, t in asym_result["Operation"].items():
        all_results.append({
            "Category": "Asymmetric-Operation",
            "Algorithm": algo,
            "FileSize_KB": 0,
            "Time_sec": t
        })

    df = pd.DataFrame(all_results)
    output_path = results_dir / 'Encrypt_results.csv'
    df.to_csv(output_path, index=False)
    print("\n" + "="*50)
    print("Experiment completed successfully!")
    print(f"Results saved to: {output_path}")
    print("="*50)
    print("\nPreview of results:")
    print(df.head(10))
    
if __name__ == "__main__":
    print("DEMO MODE")
    print("1. Hashing only")
    print("2. Symmetric only")
    print("3. Asymmetric only")
    print("4. Full experiment (original)")

    choice = input("Choose (1-4): ")

    if choice == "1":
        print("\nRunning Hashing Demo (1 MB)")
        data = create_file(1024 * 1024)          
        results = run_hashing(data)
        for algo, t in results.items():
            print(f"{algo:12}: {t:.6f} seconds")

    elif choice == "2":
        print("\nRunning Symmetric Demo (1 MB)")
        data = create_file(1024 * 1024)
        results = run_symmetric(data)
        for algo, t in results.items():
            print(f"{algo:12}: {t:.6f} seconds")

    elif choice == "3":
        print("\nRunning Asymmetric Demo")
        results = run_asymmetric()
        
        print("\nKey Generation:")
        for algo, t in results["KeyGen"].items():
            print(f"{algo:12}: {t:.4f} seconds")
        
        print("\nOperation:")
        for algo, t in results["Operation"].items():
            print(f"{algo:12}: {t:.6f} seconds")
    else:
        main()