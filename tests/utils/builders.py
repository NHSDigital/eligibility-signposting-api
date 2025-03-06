import factory

from eligibility_signposting_api.model.person import Person


class PersonFactory(factory.Factory):
    class Meta:
        model = Person

    name = "simon"
    nickname = "Baldy"
