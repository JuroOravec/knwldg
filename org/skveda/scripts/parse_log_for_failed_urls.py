import re

log_file = "log/businesses_by_name.2019-08-10_09-50-28.txt"
pattern = re.compile("(?<=\<GET\s).*?(?=\>\s\(failed\s1)")
line_identifier = "failed 1"
entry_identifier = "orsr.sk/vypis.asp"
destination = "input/businesses"

entry_urls = []
search_urls = []
with open(log_file, "r") as f:
    for line in f:
        if line_identifier in line:
            for url in pattern.findall(line):
                if entry_identifier in url:
                    entry_urls.append(url)
                else:
                    search_urls.append(url)

with open(f"{destination}_entries.txt", "w") as out:
    out.write("\n".join(entry_urls))

with open(f"{destination}_searches.txt", "w") as out:
    out.write("\n".join(search_urls))
