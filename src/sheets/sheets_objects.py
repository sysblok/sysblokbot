import logging

from sheetfu.modules.table import Item, Table
from typing import List

from .utils import convert_excel_datetime_to_string
from ..consts import TrelloCardColor
from ..strings import load
from ..trello.trello_objects import CardCustomFields, TrelloCard


logger = logging.getLogger(__name__)


class RegistryPost:
    key_title_map = {
        'name': 'Название поста',
        'author': 'Автор',
        'rubric_1': 'Рубрика',
        'rubric_2': 'Доп.Рубрика',
        'google_doc': 'Гугл.док',
        'trello': 'Трелло',
        'editor': 'Редактор',
        'cover_type': 'Тип обложки',
        'cover': 'Обложка',
        'illustrator': 'Иллюстратор',
        'date_site': 'Дата (сайт)',
        'status_site': 'Статус публикации (сайт)',
        'pin_site': '📌',
    }

    def __init__(
            self,
            card: TrelloCard,
            custom_fields: CardCustomFields,
            is_main_post: bool,
            is_archive_post: bool,
            all_rubrics: List,
    ):
        self.title = custom_fields.title
        self.authors = ','.join(custom_fields.authors)
        self.trello_url = card.url
        self.google_doc = custom_fields.google_doc
        self.editors = ','.join(custom_fields.editors)
        self.illustrators = ','.join(custom_fields.illustrators)
        self.cover = custom_fields.cover
        self.is_main_post = is_main_post
        self.is_archive_post = is_archive_post

        self._fill_rubrics(card, all_rubrics)

    def _fill_rubrics(self, card: TrelloCard, all_rubrics: List):
        # We filter BLACK cards as this is an auxiliary label
        card_rubrics = [
            label.name for label in card.labels
            if label.color != TrelloCardColor.BLACK
        ]
        self.rubric_1 = next((
            rubric.vk_tag for rubric in all_rubrics
            if rubric.name == card_rubrics[0]
        ), 'нет')
        self.rubric_2 = 'нет' if len(card_rubrics) == 1 else next((
            rubric.vk_tag for rubric in all_rubrics
            if rubric.name == card_rubrics[1]
        ), 'нет')

    def to_dict(self):
        return {
            RegistryPost.key_title_map['name']: self.title,
            RegistryPost.key_title_map['author']: self.authors,
            RegistryPost.key_title_map['rubric_1']: self.rubric_1,
            RegistryPost.key_title_map['rubric_2']: self.rubric_2,
            RegistryPost.key_title_map['google_doc']: self.google_doc,
            RegistryPost.key_title_map['trello']: self.trello_url,
            RegistryPost.key_title_map['editor']: self.editors,
            RegistryPost.key_title_map['cover_type']: 'нет' if self.is_archive_post else None,
            RegistryPost.key_title_map['cover']: 'нет' if self.is_archive_post else self.cover,
            RegistryPost.key_title_map['illustrator']: (
                'нет' if self.is_archive_post else self.illustrators
            ),
            RegistryPost.key_title_map['date_site']: 'нет' if self.is_archive_post else None,
            RegistryPost.key_title_map['status_site']: 'архив' if self.is_archive_post else None,
            RegistryPost.key_title_map['pin_site']: (
                'да' if not self.is_archive_post and self.is_main_post else 'нет'
            ),
        }


class SheetsItem:
    field_alias = {}

    def __init__(self, item: Item):
        if not self.field_alias:
            raise RuntimeError(f'empty field_alias for {self.__class__}')
        self.item = item

    def __getattr__(self, name):
        if name in self.field_alias:
            value = self.item.get_field_value(
                load(self.field_alias[name])
            )
            # Excel time format, http://www.cpearson.com/excel/datetime.htm
            # 40000 is around 2009
            # 50000 is around 2040, ph I hope Sysblok will thrive in 2040
            if type(value) == float and 40000 <= value <= 50000:
                return convert_excel_datetime_to_string(value)
            else:
                return value
        else:
            return super().__getattribute__(name)

    def __setattr__(self, name, value):
        if name in self.field_alias:
            return self.item.set_field_value(
                load(self.field_alias[name]),
                value,
            )
        else:
            return super().__setattr__(name, value)

    @classmethod
    def add_one_to_table(cls, table: Table, item_dict_alias: dict) -> Item:
        """
        This is ugly, but sheetfu doesn't have a better API
        I will fix that at some point
        """
        item_dict = {
            load(cls.field_alias[k]): v
            for k, v in item_dict_alias.items()
        }
        return cls(table.add_one(item_dict))


class HRPersonRaw(SheetsItem):
    field_alias = {
        'ts': 'sheets__hr__raw__timestamp',
        'name': 'sheets__hr__raw__name',
        'interests': 'sheets__hr__raw__interests',
        'other_contacts': 'sheets__hr__raw__other_contacts',
        'about': 'sheets__hr__raw__about',
        'email': 'sheets__hr__raw__email',
        'telegram': 'sheets__hr__raw__telegram',
        'status': 'sheets__hr__raw__status',
    }


class HRPersonProcessed(SheetsItem):
    field_alias = {
        'id': 'sheets__hr__processed__id',
        'name': 'sheets__hr__processed__name',
        'interests': 'sheets__hr__processed__interests',
        'other_contacts': 'sheets__hr__processed__other_contacts',
        'about': 'sheets__hr__processed__about',
        'hr_name': 'sheets__hr__processed__hr_name',
        'date_submitted': 'sheets__hr__processed__date_submitted',
        'telegram': 'sheets__hr__processed__telegram',
        'status': 'sheets__hr__processed__status',
        'status_novice': 'sheets__hr__processed__status_novice',
        'source': 'sheets__hr__processed__source',
        'curator': 'sheets__hr__processed__curator',
    }


class PostRegistryItem(SheetsItem):
    field_alias = {
        'name': 'sheets__post_registry__column_name',
        'vk_link': 'sheets__post_registry__column_vk_link',
        'trello': 'sheets__post_registry__column_trello'
    }
