import re
import pydantic

class UserID(pydantic.BaseModel):
	full_id :str | None = None
	friendly_name :str | None = None
	domain_name :str | None = None

	def __repr__(self):
		return self.full_id

	@pydantic.model_validator(mode="before")
	def validate_id(cls, user_id):
		if user_id.startswith('@') is False:
			raise ValueError(f"Matrix user ID's must start with an at symbol ('@')")
		if user_id.count(':') != 1:
			raise ValueError(f"Matrix user ID's must contain exactly one colon (':')")

		user, domain = user_id.split(':', 1)
		
		domain_regex = re.compile(r'(([\da-zA-Z])([_\w-]{,62})\.){,127}(([\da-zA-Z])[_\w-]{,61})?([\da-zA-Z]\.((xn\-\-[a-zA-Z\d]+)|([a-zA-Z\d]{2,})))$', re.IGNORECASE)
		if not domain_regex.match(domain):
			raise ValueError(f"Domain part of user ID must be a valid domain name: {domain}")

		values = {
			'friendly_name' : user[1:],
			'domain_name' : domain,
			'full_id' : user_id
		}

		return values