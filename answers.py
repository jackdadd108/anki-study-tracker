import re
def normalize(value):
    items=value if isinstance(value,list) else re.split(r'[\s,;&/+]+',str(value or ''))
    return sorted({str(s).strip().upper() for s in items if re.fullmatch('[A-Za-z]',str(s).strip())})
def resolve(card,options):
    def valid(value): return [x for x in normalize(value) if ord(x)-65<len(options)]
    if card.get('edited_correct_option'): return valid(card.get('correct_options') or card.get('correct_option'))
    header=re.split(r'\n\s*\n',card.get('answer',''))[0].strip()
    def text(value):return re.sub(r'[.\s]+$','',str(value).lower()).strip()
    for i,o in enumerate(options):
        if text(o)==text(header):return [chr(65+i)]
    letters=re.sub(r'^(?:correct answers?|answers?)\s*[:=-]\s*','',header,flags=re.I)
    if re.fullmatch(r'[A-Z](?:(?:\s*[,;&/+]+\s*|\s+and\s+)[A-Z])*[.]?',letters,re.I):return valid(re.sub(r'\band\b',',',letters,flags=re.I).rstrip('.'))
    found=valid(re.findall(r'(?:^|[,;\n]\s*)([A-Z])[.):]\s+',header))
    return found or valid(card.get('correct_options') or card.get('correct_option'))
def grade(selected,correct):
    chosen=normalize(selected)
    return len(chosen)==1 and chosen[0] in normalize(correct)
