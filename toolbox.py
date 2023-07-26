import openai
import json
from datetime import datetime
from datetime import timedelta
import fractal

registeredTools = []


def Tool(cls):
    cls.isTool = True
    registeredTools.append(cls)
    return cls


@Tool
class AddNewTask():
    def __init__(self):
        self.needID = True
        self.func = addNewTask
        self.schema = {
            "name": "AddNewTask",
            "description": "Add a task to a user's todo / task list",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The name / title of the task"
                    },
                    "description": {"type": "string", "description": "The description of the task"},
                    "start": {
                        "type": "string",
                        "format": "date-time",
                        "description": "The start time of the task "
                    },
                    "due": {
                        "type": "string",
                        "format": "date-time",
                        "description": "The due time of the task"
                    },
                    "status": {
                        "type": "string",
                        "description": "The status of the task",
                        "enum": ["unstarted", "in-progress", "completed"]
                    },
                    "priority": {
                        "type": "integer",
                        "description": "The priority of the task"
                    },
                    "importance": {
                        "type": "integer",
                        "description": "The importance of the task"
                    },
                    "comments": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "Comments related to the task"
                    }
                },
                "required": ["name", "description"]
            }
        }


@Tool
class SummarizeTasks():
    def __init__(self):
        self.needID = True
        self.func = summarizeTasks
        self.schema = {
            "name": "SummarizeTasks",
            "description": "Summarizes a user's tasks if a user cannot remember them, or asks for their todo / tasks / chores list",
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "description": "Instructions on how the tasks should be organized"
                    },
                }
            }
        }


@Tool
class SendSelfie():
    def __init__(self):
        self.needID = True
        self.func = sendSelfie
        self.schema = {
            "name": "SendSelfie",
            "description": "Sends a selfie to the user",
            "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "current emotion in selfie"
                        }
                    }
            }

            # in the future add expressions
        }


def summarizeTasks(userID, prompt):
    tasks = fractal.getUserData(userID)
    agent = Agent()
    return agent.Do(prompt, tasks)


def sendSelfie(userID, emotion):
    fractal.sendPhoto(r"Media\DianeSelfie.jpg", userID)
    return "Selfie sent."


def addNewTask(userID, args):
    # Need to loop over each arg, like description=args[0], but want to have the description= only defined in the class
    task = Task(**args)
    old = []
    prioritized = {}
    canWrite = False
    response = {"header": ""}
    old = fractal.getUserData(userID)

    new = {
        "name": task.name,
        "description": task.description,
        "status": task.status,
        "start": task.start,
        "due": task.due,
        "priority": task.priority,
        "importance": task.importance,
        "comments": task.comments
    }

    if old.get("values") or old.get("interests"):
        # Will need to make eval simpler and focused on priorities when given multiple tasks (Was getting importance of 8 for doing dishes!)
        # prioritized = evalTask(new, old["values"], old["interests"])
        pass

    if prioritized:
        canWrite = True
        old["tasks"].append(prioritized)
        response["header"] = "Prioritized task"
        response = prioritized
    else:
        canWrite = True
        old["tasks"].append(new)
        response["header"] = "Wasn't able to prioritize new task because user was missing either values or interests"
        response["content"] = prioritized

    if canWrite:
        with open(f"Data/{userID}/User.json", "w", encoding="utf-8") as f:
            json.dump(old, f, indent=4)

    return response


class Agent():
    def Do(self, prompt, data):
        openai.api_key = fractal.OPENAI_API_KEY
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-0613",
            messages=[
                {"role": "system", "content": f"These are your instructions, be organized and highly detailed: {prompt}"},
                {"role": "user", "content": str(data)}],
        )
        print(response)
        return response["choices"][0]["message"].get("content")


class Task():
    start_default = datetime.today().strftime("%m-%d-%Y %H:%M")
    due_default = (datetime.today() + timedelta(days=7)
                   ).strftime("%m-%d-%Y %H:%M")

    def __init__(self, name, description, start=start_default, due=due_default,
                 status="unstarted", priority=None, importance=None, comments=None):
        self.name = name
        self.description = description
        self.status = status
        self.start = start
        self.due = due
        self.priority = priority
        self.importance = importance
        self.comments = comments if comments else []


def getAvailableTools():
    return registeredTools


def evalTask(task, values=None, interests=None):
    '''Given a list of values and interests, an agent will evaluate the 
       importance and priority of a task and make changes to a task'''
    if not values or not interests:
        return None

    openai.api_key = fractal.OPENAI_API_KEY
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-0613",
        messages=[
            # {"role": "system", "content": "Given the user's interests or values, rate the priority and importance accurately"},
            {"role": "user", "content": "Analyze the user's values and interests and re-evaluate the priority and importance based on what would resonate with the user best. DATA: " + str({"task": task, "values": values, "interests": interests})}],
        functions=[
            {
                "name": "evaluateTask",
                "description": "Given the user's interests or values, evaluate each field accurately, reflecting truth",
                "parameters": {
                    "type": "object",
                    "properties": {
                        # "start": {
                        #     "type": "string",
                        #     "format": "date-time",
                        #     "description": "The start time of the task"
                        # },
                        # "due": {
                        #     "type": "string",
                        #     "format": "date-time",
                        #     "description": "The due time of the task"
                        # },
                        # "status": {
                        #     "type": "string",
                        #     "description": "The status of the task",
                        #     "enum": ["unstarted", "in-progress", "completed"]
                        # },
                        "priority": {
                            "type": "integer",
                            "description": "The priority of the task 0 - 10"
                        },
                        "importance": {
                            "type": "integer",
                            "description": "The importance of the task 0 - 10"
                        },
                        "comments": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "Comments related to the task"
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "The logic and reasoning behind the priority and importance values"
                        }
                    },
                    "required": ["priority", "importance", "comments", "reasoning"]
                }
            }],
        function_call={"name": "evaluateTask"}
    )

    print(response)


# Example dummy function hard coded to return the same weather
# In production, this could be your backend API or an external API
def get_current_weather(location, unit="fahrenheit"):
    """Get the current weather in a given location"""
    weather_info = {
        "location": location,
        "temperature": "72",
        "unit": unit,
        "forecast": ["sunny", "windy"],
    }
    return json.dumps(weather_info)


if __name__ == "__main__":
    pass  # Testing goes here
