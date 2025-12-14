import bcrypt
import os
import re
# bcrypt: used for hashing passwords securely
# os: used to check if files exist
# re: regular expressions for username validation


# Path to user data text file (stores username, hash, and role)
USER_DATA_FILE = "data/users.txt"



def hash_password(plain_text_password):
    """Convert a plain text password into a secure hashed version."""
    pass_bytes = plain_text_password.encode("utf-8")   # convert password to bytes
    salt = bcrypt.gensalt()                            # generate a random salt
    hashed_password = bcrypt.hashpw(pass_bytes, salt)  # hash password with salt
    return hashed_password


def verify_password(plain_text_password, hashed_password):
    """Check if the plain password matches the stored hashed password."""
    pass_bytes = plain_text_password.encode("utf-8")   # convert input password to bytes
    return bcrypt.checkpw(pass_bytes, hashed_password) # compare hashed versions


def register_user(username, password, role="user"):
    """"Registers a user by saving the username and hashed password and role to user.txt"""
    try:
        # Check if file exists and if username is already taken
        with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(",")
                saved_username = parts[0]

                if saved_username == username:  # if username already exists
                    return False
    except FileNotFoundError:
        # File does not exist yet — this is fine for a new project
        pass

    # Hash the user's password
    hashed_password = hash_password(password)
    hashed_password_str = hashed_password.decode("utf-8")  # convert bytes to string for saving

    # Store the new user in the text file
    with open(USER_DATA_FILE, "a", encoding="utf-8") as f:
        f.write(f"{username},{hashed_password_str},{role}\n")

    return True  # registration successful


def login_user(username, password):
    """
    Check if the username exists and verify the password and Returns the user's role if logged in
    and an error if the incorrect password is entered"""

    # If users file doesn't exist, no login can happen
    if not os.path.exists(USER_DATA_FILE):
        return None

    # Open the user file and read every stored account
    with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            parts = line.split(",")

            # Ensure at least username + hash exist
            if len(parts) >= 2:
                saved_username = parts[0]
                saved_hashed_password_str = parts[1]

                # Use stored role if it exists; otherwise default to "user"
                saved_role = parts[2] if len(parts) > 2 else "user"

                # If username matches, verify the password
                if saved_username == username:
                    stored_hash_bytes = saved_hashed_password_str.encode("utf-8")

                    if verify_password(password, stored_hash_bytes):
                        return saved_role  # login successful
                    else:
                        return None        # wrong password

    return None  # username not found at all


def validate_username(username):
    """Ensure username meets minimum security and formatting rules."""
    if len(username) < 3:
        return False, "Username must be at least 3 characters long."

    if " " in username:
        return False, "Username cannot contain spaces."

    # Only allow letters, numbers, underscores, or dashes by using regular expression
    if not re.match(r"^[A-Za-z0-9_-]+$", username):
        return False, "Username can only contain letters, numbers, underscores, or dashes."

    return True, ""  # username is valid



def validate_password(password):
    """Ensure password strong enough for basic security."""
    if len(password) < 6:
        return False, "Password must be at least 6 characters long."

    if not any(ch.isdigit() for ch in password):
        return False, "Password must contain at least one number."

    if not any(ch.isalpha() for ch in password):
        return False, "Password must contain at least one letter."

    return True, ""  # password is valid
