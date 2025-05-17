# Example script demonstrating loop translation behavior

# Currently can translate while loops
index = 0
while index < 10:
    print(index)
    index = index + 1

# Break and Continue are also translated
index = 0
while True:
    if index > 10:
        break
    else:
        print(index)
        index = index + 1   # increment index to avoid infinite loop
        continue
i=0
for i in 5:
    print(i)
    
a=[1,2,3,4,5]

for i in range(len(a)):
    print(i)
    
for i in range('a','g',2):
    print(i)
    
s='abcdefg'

for i in range(len(s)):
    print(s[i])