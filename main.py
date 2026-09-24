from agents import discovery_agent, reviewer_agent, outreach_agent
from crewai import Task, Crew, Process
from tasks import discovery_task, review_task, outreach_task

crew = Crew(
    agents=[discovery_agent, reviewer_agent, outreach_agent],
    tasks=[discovery_task, review_task, outreach_task],
    process=Process.sequential,
    planning=False,
    verbose=True
)

result = crew.kickoff()
print(result)