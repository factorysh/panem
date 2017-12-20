import sys
from passlib.hash import pbkdf2_sha256


def main():
    print(pbkdf2_sha256.hash(sys.argv[1]))
