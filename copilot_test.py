from statistics import median


def calculate_median():
    """
    Collects numbers from user input in a while loop and calculates the median.
    User types 'done' to finish input.
    Validates that inputs are valid numbers.
    """
    numbers = []
    
    print("Enter numbers one at a time. Type 'done' when finished.")
    
    while True:
        user_input = input("Enter a number (or 'done' to finish): ").strip()
        
        # Check if user is done
        if user_input.lower() == "done":
            if not numbers:
                print("Error: You must enter at least one number.")
                continue
            break
        
        # Validate input
        try:
            num = float(user_input)
            numbers.append(num)
            print(f"Added {num}. Current numbers: {numbers}")
        except ValueError:
            print(f"Error: '{user_input}' is not a valid number. Please try again.")
            continue
    
    # Calculate and return median
    result = median(numbers)
    print(f"\nMedian of {numbers} is: {result}")
    return result


if __name__ == "__main__":
    calculate_median()


##Create a message congratulating the user on successfully calculating the median, and encourage them to try again with different numbers to see how the median changes.
    print("\nCongratulations on successfully calculating the median! Feel free to try again with different numbers to see how the median changes. Happy calculating!")
    
