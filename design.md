Simple TODO with following features:
* Reminders
* Auto collapse when tasks are postponed or have a reminder
* Support of tasks hierarchies by adding ** and ***
* Tasks dependencies


Syntax:
New tasks starts with *
Subtast starts with **, can be indented
```
* Root task
  ** Subtask
```
Every task may have id assigned to it. It goes right after * and before :
```
*35: Task with id
```
All ids are assigned automatically by vim when user press *<space> in insert mode. In syntax, all ids are hidden.

All instructions to the tool goes inside []
```
* Task [remind in 2hrs]
* Another [depends: 35]
* Hidden task [hide for 3 days]
```

To add instruction, we can use autocompletion. It will suggest tasks by content and instructions itself.
Instructions can be separated by commas:
```
* Task [depends: 35, remind in 3 days]
```

Vim collects metadata in the section for Metadata: The one which is marker with:
-----------------------------------------------------------------------------------------------------------------------
Each metadata starts with #
Metadata can include:
```
#reminder for:35 started:10-dec-2019,10:15
```
Where for: accepts task id. 
Plugin will read this and can get an idea on when to remind about task (remind has duration, meta has start date)

Reminders
---------
Vim collapses all tasks which has reminders when cursor position stands on other task and it is idle for some time.
When it is time to remind about task, vim expands task (when cursor is not on the task) and when cursor is idle for some time.

Hidden Tasks
------------
Task can be marked as hidden for some time. All it's dependent tasks will be hidden as well (recursively)
