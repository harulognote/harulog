import unittest
from datetime import date, timedelta

import pet_service


class PetValidationTests(unittest.TestCase):
    def base(self, **changes):
        data = {
            'name': '하루', 'species': 'cat', 'registration_no': 'HL-001', 'sex': 'female',
            'birth_date': '2024-01-01', 'death_date': '', 'breed': 'Korean Shorthair',
            'color': '치즈', 'microchip_no': '', 'sire_id': '', 'dam_id': '',
            'status': 'active', 'notes': ''
        }
        data.update(changes)
        return data

    def test_valid_pet_is_normalized(self):
        result = pet_service.validate(self.base(name='  하루  '))
        self.assertEqual(result['name'], '하루')
        self.assertEqual(result['birth_date'], date(2024, 1, 1))
        self.assertIsNone(result['sire_id'])

    def test_future_birth_date_is_rejected(self):
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        with self.assertRaisesRegex(ValueError, '미래'):
            pet_service.validate(self.base(birth_date=tomorrow))

    def test_death_before_birth_is_rejected(self):
        with self.assertRaisesRegex(ValueError, '빠를 수 없습니다'):
            pet_service.validate(self.base(death_date='2023-12-31'))

    def test_invalid_parent_id_is_rejected(self):
        with self.assertRaisesRegex(ValueError, '부모 개체'):
            pet_service.validate(self.base(sire_id='not-a-number'))

    def test_invalid_species_is_rejected(self):
        with self.assertRaisesRegex(ValueError, '종류'):
            pet_service.validate(self.base(species='unknown-species'))

    def test_pedigree_generation_limit_shape(self):
        rows = {
            1: {'id':1,'name':'자묘','species':'cat','registration_no':'C','sex':'female','birth_date':'2024-01-01',
                'breed':'','color':'','status':'active','photo_path':'','sire_id':2,'dam_id':3},
            2: {'id':2,'name':'부','species':'cat','registration_no':'S','sex':'male','birth_date':'2020-01-01',
                'breed':'','color':'','status':'active','photo_path':'','sire_id':None,'dam_id':None},
            3: {'id':3,'name':'모','species':'cat','registration_no':'D','sex':'female','birth_date':'2020-01-01',
                'breed':'','color':'','status':'active','photo_path':'','sire_id':None,'dam_id':None},
        }
        tree = pet_service._tree(rows, 1, 2)
        self.assertEqual(tree['sire']['name'], '부')
        self.assertEqual(tree['dam']['name'], '모')
        self.assertNotIn('sire', tree['sire'])


if __name__ == '__main__':
    unittest.main()

