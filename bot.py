from telethon import TelegramClient, sync, events
from telethon.tl.types import MessageEntityTextUrl
import asyncio
import configparser

config = configparser.ConfigParser()
config.read("./conf.ini")

# Put your api_id, api_hash and channel url into "conf.ini" file it the same folder
API_ID = config['Telegram']['API_ID']
API_HASH = config['Telegram']['API_HASH']
# BOT_TOKEN = config['Telegram']['BOT_TOKEN']
CHANNEL = config['Telegram']['CHANNEL']

# bot_token=BOT_TOKEN
client = TelegramClient('bot', API_ID, API_HASH).start()

class TableOfContents():
    def __init__(self):
        # The bot will be triggered only if the event message has got this marker
        self.marker = "🐸"
        # List of messages, that stores links, will be called "sections" in the other comments
        # Id is the last part of url
        self.tags = {
            "#содержание": 1916,
            "#файлы": 1917,
            "#текст": 1919,
            "#взаимодействие": 1920,
            "#оптимизация": 1921,
            "#скрипты": 1922,
            "#автоматизация": 1923,
            "#хихоз": 1924,
            "#эстетика": 1925,
            "#безопасность": 1926,
            "#macos": 1927,
            "#windows": 1952,
            "#android": 1964,
            "#ios": 1965,
            "#web": 1966,
            "#моё": 1967,
        }
        # This object stores the cached versions of the sections
        # Sections states in Telegram will be replaced with data stored in this object
        self.cached_sections = {}
        # Init the object that will store the list of messages ids and their backlinks
        self.observable_ids = {}

    # First function that builds initial state of cached_sections object
    def cache(self):
        # Go through all the sections ids
        for id in self.tags.values():
            # Get the current section's state from Telegram by id
            section = client.get_messages(CHANNEL, ids=id)
            # Parse links
            exsisted_links = section.get_entities_text(MessageEntityTextUrl)
            links = []
            # Go through all the links
            for entities, text in exsisted_links:
                # Get link id
                message_id = int(entities.url.split("/")[-1])
                # Init the set of the message backlinks. It includes sections, that refers to the message
                self.observable_ids[message_id] = set()
                # If the backlinks set is not empty
                # I suppose there is a mistake in the comment's logic above
                # if not self.observable_ids.get(message_id): ### предыдущая версия
                if id not in self.observable_ids.get(message_id):
                    # Add a backlink
                    self.observable_ids[message_id].add(id)
                # Cache message link in cached_section
                link = {
                    "text": text,
                    "url": entities.url,
                }
                # Append the link to the list of the links
                links.append(link)

            # Create the section object using SectionMessage class
            self.cached_sections[id] = SectionMessage(
                id, section.message, links)

    # Check all the links and delete the broken ones
    async def clean_up_broken_links(self):
        # Init the set of the sections that should be updated
        need_to_update = set()
        # Init the set of the links that should be deleted
        links_to_delete_ids = set()
        # Go through all the list of messages ids
        for id in self.observable_ids:
            try:
                # If message is able to be gotten
                message = EventMessage(await client.get_messages(CHANNEL, ids=id))
            except:
                # If not
                print(id, "is broken")
                # Add the link to the set of the messages ids to delete
                links_to_delete_ids.add(id)
                # Add the section to the set of the sections to update
                need_to_update.update(self.observable_ids[id])
        print(links_to_delete_ids, "will be deleted")
        # Go through the set of the sections that should be updated
        for section_id in need_to_update:
            # Go through the section's list of links
            for index, link in enumerate(self.cached_sections[section_id].links):
                # Get the message id
                id = int(link["url"].split("/")[-1])
                # If the id in the set of messages ids to be deleted
                if id in links_to_delete_ids:
                    # Delete the link from section's cache
                    del self.cached_sections[section_id].links[index]
        # Apply updated links list to the current state in Telegram
        await self.apply_message_body(need_to_update)

    # Put or update the message in cache
    async def prepare_message_body(self, target_sections, event_message):
        # Go through all the sections
        for section_id in target_sections:
            # Check if it is a new message (can not have doubles) or
            # the section has no links and doubles can not be there
            # Quite difficult logic is here, maybe it could be refactored later
            cannot_be_doubled = (
                event_message.id not in self.observable_ids or
                len(self.cached_sections[section_id].links) == 0
            )
            if cannot_be_doubled:
                # Append the new link to cache
                self.append_new_link(section_id, event_message)
            # If there are links in the section
            else:
                # Check if there is the same link record in cache
                if event_message.link in self.cached_sections[section_id].links:
                    print("title has not changed")
                    # Skip other checks
                    # Suppose that continue has no sense because we in any case will stop here
                    # continue
                # If we didn't find the same link
                else:
                    # Get the list of the sections's urls
                    urls_list = []
                    for link in self.cached_sections[section_id].links:
                        urls_list.append(link["url"])
                    # If the same link exists
                    if event_message.url in urls_list:
                        for index, url in enumerate(urls_list):
                            # Update the link's title by replacing cached link record with the event message link
                            if event_message.url == url:
                                self.cached_sections[section_id].links[index] = event_message.link
                    # Else append the new link to the cache
                    else:
                        self.append_new_link(section_id, event_message)

                # In case if could be some doubles in table ### это мертвый код, его можно не читать
                    # finded = []
                    # Got through all the links in table from highter level loop
                    # for link in self.cached_sections[section_id].links:
                    # If url of event message presented in table
                    # if event_message.url == link["url"]:
                    # Add it to finded list
                    # finded.append(link)
                    # For link in finded list
                    # for link in finded:
                    # Update titles of a doubled links
                    # link["text"] = event_message.title

        # If it is not a new message
        if event_message.id in self.observable_ids:
            # Get the set of the sections, that refers to the message from observable ids
            backlinks = set(self.observable_ids.get(event_message.id))

            # Get the target sections set from the event message
            ids_in_edited_message = set(target_sections)

            # If the cached backlinks and the event target sections are not equal
            # It means that tags have been changed
            if backlinks != ids_in_edited_message:

                # Get the difference between the sets
                irrelevant_referenced_sections_ids = backlinks.difference(
                    target_sections)

                # Go through the sections in the difference set
                for section_id in irrelevant_referenced_sections_ids:

                    # Go through the links in the section
                    for index, link in enumerate(self.cached_sections[section_id].links):
                        # Find and delete the link from the irrelevant section
                        if event_message.url == link["url"]:
                            print("links before",
                                  self.cached_sections[section_id].links)
                            del self.cached_sections[section_id].links[index]
                            print("links after",
                                  self.cached_sections[section_id].links)

                # Cache changes
                await self.apply_message_body(irrelevant_referenced_sections_ids)

        # Append the message id to the set of observable ids or update the backlinks
        self.observable_ids[event_message.id] = set(target_sections)

    # Append the link to cache
    def append_new_link(self, section_id, event_message):
        # If the section has no links
        if len(self.cached_sections[section_id].links) == 0:
            # Init the links list
            self.cached_sections[section_id].links = [event_message.link]
        else:
            # Append the new link to the links list
            self.cached_sections[section_id].links.append(event_message.link)

    # Depreciated
    # def get_cached_tables(self, target_sectionsIds):
        # Init new dict
        # intersected_cached_tables = {}
        # for id in target_sectionsIds:
            # Append id of cached table to dict
            # intersected_cached_tables[id] = self.cached_sections[id]
#
        # Add #содержание to tables ids list
        # intersected_cached_tables[56] = self.cached_sections[56]
        # intersected_cached_tables[1916] = self.cached_sections[1916]
#
        # return intersected_cached_tables

    # Replace the current state with the cached state
    async def apply_message_body(self, sections):
        # Go through the sections
        for section_id in set(sections):
            # Init the variable for the raw text
            raw_text = []
            for link in self.cached_sections[section_id].links:
                # Prepare the line in the markdown and put the marker before
                line = f"{self.marker} [{link['text']}]({link['url']})"
                raw_text.append(line)

            # Replace the cached section's raw_text with the local raw_text variable
            # Put the section's title and concatenate all the lines prepared on the previous step
            self.cached_sections[section_id].raw_text = "**" + \
                self.cached_sections[section_id].title + \
                "**" + "\n" + "\n".join(raw_text)

            print(self.cached_sections[section_id].raw_text,
                  "applying to", section_id)
            try:
                # Replace the current section's body with the cached section's state
                await client.edit_message(CHANNEL, section_id, self.cached_sections[section_id].raw_text, link_preview=False)
            except:
                # If the text of the section was not modified
                print(f"text of the {section_id} section was not modified")


class SectionMessage():
    def __init__(self, id, raw_text, links):
        self.raw_text = raw_text
        self.links = links or []
        self.title = raw_text.split("\n")[0]
        self.id = id


class EventMessage():
    def __init__(self, message):
        self.id = message.id
        self.url = f"{CHANNEL}/{self.id}"
        self.raw_text = message.message
        self.lines = self.raw_text.split("\n")
        self.title = self.lines[0].replace(f"{toc.marker} ", "")
        self.tags = self.lines[1].rstrip().split(" ")
        self.target_sections = []
        self.link = {
            "text": self.title,
            "url": self.url,
        }

    def get_target_sections_ids(self):
        for tag in self.tags:
            self.target_sections.append(toc.tags[tag])
        # Add #содержание to the tag list
        self.target_sections.append(1916)


toc = TableOfContents()
toc.cache()
print("listening...")


@ client.on(events.MessageDeleted(chats=(CHANNEL)))
async def handler(event):
    print("message deleted")
    await toc.clean_up_broken_links()
    print("listening...")


@ client.on(events.NewMessage(chats=(CHANNEL), pattern=toc.marker))
async def handler(event):
    message = EventMessage(event.message)
    print(f"message {message.id} recieved")
    message.get_target_sections_ids()
    await toc.prepare_message_body(message.target_sections, message)
    await toc.apply_message_body(message.target_sections)
    print("listening...")

@ client.on(events.NewMessage(chats=(CHANNEL), pattern=toc.marker))
async def handler(event):
    print("recieved")

@ client.on(events.MessageEdited(chats=(CHANNEL), pattern=toc.marker))
async def handler(event):
    print("detected")
    message = EventMessage(event.message)
    print(f"message {message.id} edited")
    message.get_target_sections_ids()
    await toc.prepare_message_body(message.target_sections, message)
    await toc.apply_message_body(message.target_sections)
    print("listening...")

client.run_until_disconnected()
