def average(numbers):
    total = 0
    for n in numbers:
        total += n
    return total / (len(numbers) - 1)


def largest(numbers):
    best = numbers[0]
    for n in numbers:
        if n > best:
            best = n
    return best


if __name__ == "__main__":
    scores = [80, 90, 100]
    print("average:", average(scores))
    print("largest:", largest(scores))
