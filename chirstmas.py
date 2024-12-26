
def is_christmas():
    result = "```"
    result += ('\n'.join
               ([''.join
                 ([('Merry Christmas'[(x-y) % 15]
                    if ((x*0.05)**2+(y*0.1)**2-1)
                     ** 3 - (x*0.05)**2*(y*0.1)
                     ** 3 <= 0 else ' ')
                  for x in range(-30, 30)])
                for y in range(15, -15, -1)]))
    result += "Merry Christmas```"
    return result


result = is_christmas()
print(result)
