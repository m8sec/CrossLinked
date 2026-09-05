import unittest
from crosslinked.models import Candidate, ReviewedCandidate
from crosslinked.quality import classify, normalize_name, review


class QualityTests(unittest.TestCase):
    def check(self, title, expected, **kwargs):
        record = {'name': title.split(' - ')[0], 'text': title, 'url': 'https://www.linkedin.com/in/example'}
        result = classify(record, 'Example University', **kwargs)
        self.assertIsInstance(result, ReviewedCandidate)
        self.assertEqual(result.classification, expected, result)
        self.assertTrue(result.reason)
        self.assertEqual(result.text, title)
        self.assertEqual(result.original_name, record['name'])
        return result

    def test_current_student(self):
        for role in ('Student at', 'PhD student at', 'Graduate student at', 'Post-graduate student at', 'Studying Chemistry at'):
            self.check('Jane Doe - ' + role + ' Example University', 'current_student_candidate')

    def test_staff(self):
        self.check('Jane Doe - Lecturer at Example University', 'current_staff_candidate')
        self.check('Jane Doe - Research Associate - Example University', 'current_staff_candidate')

    def test_former(self):
        for role in ('Former student at', 'Graduate from', 'Retired professor at', 'Alumna of'):
            self.check('Jane Doe - ' + role + ' Example University', 'former_affiliation')
        self.check('Jane Doe - Professor Emeritus - Example University', 'uncertain')

    def test_prospective_and_group_roles(self):
        self.check('Jane Doe - Incoming student at Example University', 'uncertain')
        self.check('Jane Doe - President at Example University Drama Society', 'uncertain')
        self.check('Jane Doe - Graduate student - Example University', 'current_student_candidate')

    def test_missing_relation(self):
        self.check('Jane Doe - Example University', 'uncertain')
        self.check('Jane Doe - Lecturer at Example ...', 'uncertain')

    def test_reversed_institution(self):
        self.check('Jane Doe - Lecturer at University of Example', 'organization_mismatch')
        self.check('Jane Doe - Lecturer at University of Example', 'current_staff_candidate', aliases=['University of Example'])

    def test_conflicting_organizations(self):
        self.check('Jane Doe - Example University | Lecturer at University of Example', 'uncertain')
        self.check('Jane Doe - Lecturer at Other College', 'organization_mismatch', excluded_orgs=['Other College'])

    def test_group(self):
        self.check('Example University Rowing Club - Example University', 'non_person')

    def test_names(self):
        examples = {'Dr Nicole Example': 'nicole example', 'Jane Doe, PhD': 'jane doe',
                    'Alex Example, EdD (IEAA-SF)': 'alex example', 'John Example CFRE': 'john example',
                    'Anne-Marie Dupont': 'anne-marie dupont', "Sean O’Neill": "sean o'neill",
                    'Marthin du Plooy': 'marthin du plooy'}
        for raw, expected in examples.items():
            self.assertEqual(normalize_name(raw), expected)

    def test_initial_not_expanded(self):
        record = self.check('Jane B. - Lecturer at Example University', 'current_staff_candidate')
        self.assertTrue(record.name_issue)
        self.assertEqual(record.name, 'jane b.')

    def test_word_boundaries(self):
        self.check('Jane Doe - Lecturer at NotExample University', 'uncertain')

    def test_old_other_affiliation_does_not_exclude_target(self):
        self.check('Jane Doe - Lecturer at Example University | Graduate from Other College', 'current_staff_candidate')

    def test_typed_input_and_review_dict(self):
        candidate = Candidate(name='Dr Jane Doe', text='Dr Jane Doe - Lecturer at Example University',
                              url='https://www.linkedin.com/in/jane', provider='searxng', observed_at='2026-01-01')
        reviewed = review([candidate], 'Example University')[0]
        self.assertEqual(reviewed.classification, 'current_staff_candidate')
        self.assertEqual(reviewed.provider, 'searxng')
        data = reviewed.to_dict()
        self.assertEqual(data['original_name'], 'Dr Jane Doe')
        self.assertEqual(data['name'], 'jane doe')
        self.assertEqual(data['observed_at'], '2026-01-01')
        # Re-reading a review record keeps the original spelling for a second pass.
        self.assertEqual(Candidate.from_dict(data).name, 'Dr Jane Doe')

    def test_nameless_record_flagged_not_dropped(self):
        result = classify({'text': 'Lecturer at Example University'}, 'Example University')
        self.assertTrue(result.name_issue)
