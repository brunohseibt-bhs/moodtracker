##Change - Bruno
##Change 2
##Change 3

def count_vowels(text):
    vowels = "aeiouAEIOU"
    count = 0

    for char in text:
        if char in vowels:
            count += 1

    return count


# User input
user_text = input("Enter a string: ")

# Function call
total_vowels = count_vowels(user_text)

print("Number of vowels:", total_vowels)
