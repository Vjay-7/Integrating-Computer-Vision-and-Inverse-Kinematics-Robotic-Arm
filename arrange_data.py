import csv

with open('save_angles.csv', 'r', newline='') as infile:
    reader = list(csv.reader(infile))
    header = reader[0]  # Keep the header
    data = reader[1:]   # The actual data rows

# Sort the data by Column 1 (index 0) and Column 2 (index 1) as floats
sorted_data = sorted(data, key=lambda row: (float(row[0]), float(row[1])))

# Write the sorted data to a new CSV file
with open('sorted_output.csv', 'w', newline='') as outfile:
    writer = csv.writer(outfile)
    writer.writerow(header)        # Write header first
    writer.writerows(sorted_data)  # Then the sorted rows
