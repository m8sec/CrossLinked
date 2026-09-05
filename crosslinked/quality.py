"""Conservative, explainable classification of search evidence, not verification."""
import csv
import re
from unidecode import unidecode


def normalize_name(value):
    name = re.sub(r'\s+', ' ', unidecode(value)).strip()
    name = re.sub(r'^(?:(?:dr|prof|professor|mr|mrs|ms|miss)\.?\s+)+', '', name, flags=re.I)
    # Only strip known qualifications, never arbitrary name components.
    credentials = r'(?:ph\.?d\.?|edd|md|mba|msc|bsc|cfre|sfhea|fhea|ieaa-sf)'
    name = re.sub(r'[,\s]+(?:' + credentials + r'|\(' + credentials + r'\))(?:[,\s]+.*)?$', '', name, flags=re.I)
    return name.strip(' ,').lower()


def phrase(value, text):
    return bool(re.search(r'(?<!\w)' + re.escape(value.casefold()) + r'(?!\w)', text.casefold()))


def classify(record, organization, aliases=(), excluded_orgs=()):
    out = dict(record)
    original = record.get('name', '')
    name = normalize_name(original)
    text = record.get('text', '')
    # Do not infer affiliation from a URL or the query itself.
    evidence = text or record.get('title', '')
    out.update(name=name, original_name=original, classification='uncertain',
               reason='', name_issue='', evidence_status='unverified search evidence')
    tokens = name.split()
    if len(tokens) < 2 or any(len(t.strip('.')) < 2 for t in (tokens[:1] + tokens[-1:])):
        out['name_issue'] = 'Incomplete name or initial; manual review required'
    elif not re.fullmatch(r"[a-z]+(?:[-'][a-z]+)*(?: [a-z]+(?:[-'][a-z]+)*)+", name):
        out['name_issue'] = 'Unresolved punctuation or qualification; manual review required'

    def decide(category, reason):
        out.update(classification=category, reason=reason)
        return out

    if re.search(r'\b(university|society|club|team|department|school|centre|center|rowing|students.? union)\b', name):
        return decide('non_person', 'Name resembles an organization or group account')
    accepted = [organization] + list(aliases)
    matches = [term for term in accepted if term and phrase(term, evidence)]
    rejected = [term for term in excluded_orgs if term and phrase(term, evidence)]
    # Reversed university names are deliberately not automatic aliases.
    if organization.lower().endswith(' university'):
        reversed_name = 'University of ' + organization[:-len(' University')]
        if not any(term.casefold() == reversed_name.casefold() for term in accepted) and phrase(reversed_name, evidence):
            rejected.append(reversed_name)
    if rejected:
        return decide('uncertain' if matches else 'organization_mismatch',
                      'Conflicting organization evidence: ' + ', '.join(rejected))
    if not matches:
        return decide('uncertain', 'Target organization not explicit in saved title')
    # Check relation clauses individually so an old affiliation elsewhere does
    # not automatically exclude a current target affiliation.
    clauses = re.split(r'\s+[|;]\s+|\s+[-–—]\s+', evidence)
    target_clauses = [c for c in clauses if any(phrase(term, c) for term in matches)]
    target_text = ' '.join(target_clauses)
    former = r'\b(former|previously|retired|alumn\w*|graduate(?:d)?(?:\s+(?:of|from))?)\b'
    student = r'\b(student|studying|phd candidate|doctoral candidate|undergraduate|postgraduate)\b'
    staff = r'\b(professor|lecturer|researcher|research associate|research fellow|fellow|officer|manager|director|dean|chancellor|president|engineer|analyst|advisor|adviser|librarian|technician|chief|staff)\b'
    if re.search(r'\b(emeritus|incoming|prospective|aspiring|applicant)\b', evidence, re.I):
        return decide('uncertain', 'Honorary or prospective status does not establish current staff/student affiliation')
    if re.search(r'\b(society|club|students.? union)\b', target_text, re.I):
        return decide('uncertain', 'Student group role does not independently establish employment or enrollment')
    former_hit = re.search(former, target_text, re.I)
    if former_hit:
        # "post-graduate student" and "graduate student" describe enrollment.
        cleaned = re.sub(r'\b(?:post[- ]?)?graduate student\b', 'student', target_text, flags=re.I)
        if re.search(former, cleaned, re.I):
            return decide('former_affiliation', 'Title explicitly describes a former/graduate affiliation')
    if re.search(student, target_text, re.I):
        return decide('current_student_candidate', 'Title describes study at target; current enrollment unverified')
    if re.search(staff, target_text, re.I):
        return decide('current_staff_candidate', 'Title describes a role at target; current employment unverified')
    # "Name - Role - Organization" is common, but only use the adjacent role.
    for i, clause in enumerate(clauses):
        if i > 0 and any(phrase(term, clause) for term in matches):
            previous = clauses[i - 1]
            previous = re.sub(r'\b(?:post[- ]?)?graduate student\b', 'student', previous, flags=re.I)
            if re.search(former, previous, re.I):
                return decide('former_affiliation', 'Adjacent role describes former affiliation')
            if re.search(student, previous, re.I):
                return decide('current_student_candidate', 'Adjacent role describes study; enrollment unverified')
            if re.search(staff, previous, re.I):
                return decide('current_staff_candidate', 'Adjacent role describes employment; employment unverified')
    return decide('uncertain', 'Organization mentioned without an explicit staff/student relationship')


def review(records, organization, aliases=(), excluded_orgs=()):
    return [classify(r, organization, aliases, excluded_orgs) for r in records]


def write_review(path, records):
    fields = ['original_name', 'name', 'classification', 'reason', 'name_issue',
              'evidence_status', 'title', 'url', 'text', 'snippet', 'engines', 'observed_at']
    with open(path, 'w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(records)
