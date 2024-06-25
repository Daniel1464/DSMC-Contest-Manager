import json
import discord

from contest import Contest
from team import Team
from question import Question
from contestperiod import ContestPeriod
import os
from exceptions import (
    AnswersAlreadySubmittedException,
    MemberInAnotherTeamException,
    MemberNotInTeamException,
    MemberNotInvitedException,
    OwnerLeaveTeamException,
    WrongPeriodException,
    TeamSizeExceededException,
    TeamNameException,
)

import traceback
import logging
from dotenv import load_dotenv
load_dotenv("secrets.env")

intents = discord.Intents.default()
intents.members = True
client: discord.Client = discord.Client(intents=intents)
tree: discord.app_commands.CommandTree = discord.app_commands.CommandTree(client)

# constants
GUILD = discord.Object(id=624314920158232616)
DANIEL_USER_ID = 614549755342880778

assert GUILD is not None


async def contest_name_autocompletion(interaction, current: str) -> list:
    with open('data/generalContestInfo.json', 'r') as file:
        contest_names = json.load(file)['allContestNames']
    data = []
    for contest_name in contest_names:
        data.append(discord.app_commands.Choice(name=contest_name.lower(), value=contest_name))
    return data


async def user_team_name_autocompletion(interaction, current: str):
    contest_name = interaction.namespace.contest_name
    contest = Contest.from_json(contest_name)
    team_name_choices = []
    for team in contest.teams:
        if interaction.user.id in team.invited_member_ids or interaction.user.id == team.owner_id:
            team_name_choices.append(discord.app_commands.Choice(name=team.name.lower(), value=team.name))
    return team_name_choices


async def all_team_names_autocompletion(interaction, current: str):
    contest = Contest.from_json(interaction.namespace.contest_name)
    team_name_choices: list[discord.app_commands.Choice] = []
    for team in contest.teams:
        team_name_choices.append(discord.app_commands.Choice(name=team.name.lower(), value=team.name))
    return team_name_choices


def get_member_repr(interaction, member_id: int) -> str:
    member = interaction.guild.get_member(member_id)
    if member is None:
        return "(Member not found)"
    else:
        return member.name


@client.event
async def on_ready():
    print("Ready!")


@tree.error
async def on_app_command_error(interaction, error):
    await interaction.response.send_message(
        "Sorry, there was a problem with the bot, so an uncaught error has occurred. "
        "Please consult @DanielRocksUrMom for help.")
    daniel = client.get_user(DANIEL_USER_ID)
    if daniel:
        channel = await daniel.create_dm()
        stack_trace = traceback.format_exc()
        with open('latest_error.log', 'w+') as file:
            file.write(stack_trace)
        await channel.send(f"Hey Daniel, the user '{interaction.user.name}' just caused an error in your code.")
        await channel.send("This is the error file: ", file=discord.File("latest_error.log"))
        logging.warning(stack_trace)
    else:
        print("Failed to write to disk.")
        logging.warning(error)


@tree.command(name="help",
              description="The starting point for the bot.",
              guild=GUILD)
async def help_command(interaction):
    await interaction.response.send_message(
        """
    The DSMC contest bot is a bot that manages DSMC competitions.
    See the bot page for descriptions on each of it's commands. 

    Basic Commands for Test-Takers: 
    /register_team 
    /join_team - needs an invitation 
    /answer_question 
    /submit_all_answers - Cannot be undone! 
    /leave_current_team - Owners must /transfer_ownership first 
    /show_answers - Shows your team's answers(not the correct ones) 
    /invite_member 
    /transfer_ownership - if you are the team's owner 
    /change_team_name 

    Commands that show the contest status: 
    /all_contest_competitors 
    /show_questions 
    /show_teams 
    /contest_period 
    /team_rankings 
    /link - Gets PDF/overleaf link 
        """
    )


@tree.command(name="create_contest",
              description="[Mod Only] Creates a new Contest.",
              guild=GUILD)
@discord.app_commands.checks.has_any_role('Olympiad Team', 'Olympiad Manager')
async def create_contest(interaction, name: str, pdf_link: str, team_size_limit: int | None = None):
    with open("data/generalContestInfo.json", "r") as file:
        data_dict = json.load(file)
        if name in data_dict['allContestNames']:
            await interaction.response.send_message("A contest with name " + name + " already exists.", ephemeral=True)
            return
    Contest(name.lower(), pdf_link, team_size_limit).update_json()
    await interaction.response.send_message("Contest successfully created!")


@tree.command(name="all_contest_competitors",
              description="Displays all contest competitors.",
              guild=GUILD)
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
async def all_contest_competitors(interaction, contest_name: str):
    contest = Contest.from_json(contest_name)
    all_participants = [get_member_repr(interaction, member_id) for member_id in contest.registered_members]
    all_invited_participants = [get_member_repr(interaction, member_id) for member_id in contest.invited_members]
    await interaction.response.send_message("These people are currently in a team: \n" + str(
        all_participants) + "\n These people are currently invited to a team: " + str(all_invited_participants))


@tree.command(name="register_team",
              description="Registers a team into a contest.",
              guild=GUILD)
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
async def register_team(interaction, contest_name: str, team_name: str, member_two: discord.Member | None = None,
                        member_three: discord.Member | None = None, member_four: discord.Member | None = None):
    contest = Contest.from_json(contest_name)
    potential_current_team: Team | None = contest.get_team_of_user(interaction.user.id)
    if potential_current_team:
        await interaction.response.send_message(f"You seem to already be in team {potential_current_team.name}.")
        return
    invite_list: list[discord.Member] = []
    if member_two:
        invite_list.append(member_two)
    if member_three:
        invite_list.append(member_three)
    if member_four:
        invite_list.append(member_four)
    try:
        new_team = Team(
            contest_instance=contest,
            name=team_name,
            owner_id=interaction.user.id
        )
        contest.add_team(new_team)
        await interaction.response.send_message(
            f"Team '{team_name}' has been added to the contest with {[member.display_name for member in invite_list]}"
            f" invited. In order for users to join your team, they must use /join_team.")
        for member in invite_list:
            new_team.invite_member(member.id)
            channel = await member.create_dm()
            await channel.send(
                f"The user {interaction.user} has invited you to join the team '{team_name}'"
                f"for the contest '{contest_name}'. In order to join, "
                f"use /join_team in the Mathematics Server (not in the DMs)."
                f"If you don't want to join, or if you're already in another team, ignore this message.")
        contest.update_json()
    except WrongPeriodException:
        await interaction.response.send_message(
            "You can only create a team when this contest is in it's signup phase. Sorry!")
    except TeamNameException:
        await interaction.response.send_message("There is already a team with the name " + team_name)


@tree.command(name="invite_members",
              description="Invites more members to your team.",
              guild=GUILD)
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
async def invite_more_members(interaction, contest_name: str, member_one: discord.Member | None = None,
                              member_two: discord.Member | None = None, member_three: discord.Member | None = None):
    contest = Contest.from_json(contest_name)
    success_messages: list[str] = []
    user_team = contest.get_team_of_user(interaction.user.id)
    if user_team is None:
        await interaction.response.send_message("Hmmm... It looks like you are not in a team yet.")
        return
    if member_one:
        user_team.invite_member(member_one.id)
        success_messages.append(f"{member_one.name} has been successfully invited.")
    if member_two:
        user_team.invite_member(member_two.id)
        success_messages.append(f"{member_two.name} has been successfully invited.")
    if member_three:
        user_team.invite_member(member_three.id)
        success_messages.append(f"{member_three.name} has been successfully invited.")
    contest.update_json()
    await interaction.response.send_message("\n".join(success_messages))


@tree.command(name="join_team",
              description="Join one of the teams you were invited to.",
              guild=GUILD)
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion, team_name=user_team_name_autocompletion)
async def join_team(interaction, contest_name: str, team_name: str):
    contest = Contest.from_json(contest_name)
    new_team = contest.get_team(team_name)
    if interaction.user.id in new_team.member_ids + [new_team.owner_id]:
        await interaction.response.send_message(
            "Looks like you are already in this team. To leave, use /leave_current_team.",
            ephemeral=True)
        return
    try:
        new_team.register_member(interaction.user.id)
        await interaction.response.send_message(
            f"Hooray! You have officially joined team {team_name}! to leave, use /leave_current_team.")
        contest.update_json()
    except MemberNotInvitedException:
        await interaction.response.send_message(
            "Hmmm.... It seems that you haven't been invited to this team.",
            ephemeral=True)
    except MemberInAnotherTeamException:
        await interaction.response.send_message(
            "You've already joined another team! Use /leave_current_team to leave your current team, "
            "then use /join_team to join this one.",
            ephemeral=True)
    except TeamSizeExceededException:
        await interaction.response.send_message(f"The team size limit of {contest.team_size_limit} has been exceeded.")


@tree.command(name="change_team_name",
              description="Change the name of the team you are in.",
              guild=GUILD)
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
async def change_team_name(interaction, contest_name: str, new_team_name: str):
    contest = Contest.from_json(contest_name)
    team: Team | None = contest.get_team_of_user(interaction.user.id)
    if team:
        previous_name = team.name
        team.name = new_team_name
        contest.update_json()
        await interaction.response.send_message(
            "The team that was previously referred to as '" +
            previous_name + "' now has the name '" + team.name + "'."
        )
    else:
        await interaction.response.send_message("It seems that you are not in a team currently.", ephemeral=True)


@tree.command(name="change_team_size_limit",
              description="[Mod Only] Modifies the team size limit for a contest.",
              guild=GUILD)
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
@discord.app_commands.checks.has_any_role('Olympiad Team', 'Olympiad Manager')
async def modify_team_size_limit(interaction, contest_name: str, size_limit: int):
    contest = Contest.from_json(contest_name)
    contest.team_size_limit = size_limit
    contest.update_json()
    await interaction.response.send_message("Team size limit has been updated to " + str(size_limit) + ".")


@tree.command(name="leave_current_team",
              description="Leaves your current team in the respective contest.",
              guild=GUILD)
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
async def leave_current_team(interaction, contest_name: str):
    contest = Contest.from_json(contest_name)
    user_team = contest.get_team_of_user(interaction.user.id)
    if user_team is None:
        await interaction.response.send_message("Hmmm... You don't seem to be in a team as of now.", ephemeral=True)
    else:
        try:
            user_team.remove_member(interaction.user.id)
            contest.update_json()
            await interaction.response.send_message("You have officially left your current team.")
        except OwnerLeaveTeamException:
            await interaction.response.send_message(
                "As the owner of this team, you cannot leave. You must either delete the team or transfer ownership "
                "to another person(via the /transfer_ownership command)")


@tree.command(name="transfer_ownership",
              description="If you are the owner of a team, transfers ownership to another person within your team.",
              guild=GUILD)
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
async def transfer_ownership(interaction, contest_name: str, new_owner: discord.Member):
    try:
        contest = Contest.from_json(contest_name)
        player_team = contest.get_team_of_user(interaction.user.id)
        if player_team is None:
            await interaction.response.send_message("it looks like you are not in a team currently.")
        elif interaction.user.id == player_team.owner_id:
            player_team.transfer_ownership(new_owner.id)
            contest.update_json()
            await interaction.response.send_message(f"Ownership has been successfully transferred to {new_owner}!")
        else:
            await interaction.response.send_message(
                "Sorry, you're not the owner of the team you're in, so you cannot transfer ownership.", ephemeral=True)
    except MemberNotInTeamException:
        await interaction.response.send_message(
            "The member that you tried to transfer ownership in is not in the team(or hasn't accepted the invite yet).")


@tree.command(name="unregister_team",
              description="Unregisters your team.",
              guild=GUILD)
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
async def unregister_team(interaction, contest_name: str):
    contest = Contest.from_json(contest_name)
    user_team = contest.get_team_of_user(interaction.user.id)
    if user_team is None:
        await interaction.response.send_message("Hmm.... You don't seem to be in a team as of now.", ephemeral=True)
    elif user_team.owner_id != interaction.user.id:
        await interaction.response.send_message(
            "Holdup! You can't delete this team, as it was created by someone else. "
            "Ask the creator to delete the team. If you want to leave, use /leave_current_team.",
            ephemeral=True)
    else:
        contest.remove_team(user_team)
        for member_id in user_team.member_ids:
            channel = await interaction.guild.get_member(member_id).create_dm()
            await channel.send(
                f"The original owner of team {user_team.name} has deleted this team. "
                f"To sign up for another team, ask another team owner to invite you, then use /join.")
        await interaction.response.send_message("Success!")
        contest.update_json()


@tree.command(name="add_question",
              description="[Mod Only] Adds a question into a contest.",
              guild=GUILD)
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
@discord.app_commands.checks.has_any_role('Olympiad Team', 'Olympiad Manager')
async def add_question(interaction, contest_name: str, answer: float, points: int, problem_number: int | None = None):
    contest = Contest.from_json(contest_name)
    try:
        if problem_number is None:
            contest.add_question(Question(contest, answer, points))
        else:
            contest.add_question(Question(contest, answer, points), problem_number)
        contest.update_json()
        await interaction.response.send_message("Success!")
    except WrongPeriodException:
        await interaction.response.send_message(
            "currently, the contest is underway. You cannot add questions at this time.", ephemeral=True)
    except IndexError:
        await interaction.response.send_message("Hmm.... your question index is out of bounds", ephemeral=True)


@tree.command(name="remove_question", description="[Mod Only] Removes a question from a specified contest.",
              guild=GUILD)
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
@discord.app_commands.checks.has_any_role('Olympiad Team', 'Olympiad Manager')
async def remove_question(interaction, contest_name: str, question_number: int):
    contest = Contest.from_json(contest_name)
    try:
        contest.remove_question(question_number)
        contest.update_json()
        await interaction.response.send_message("Question with number " + str(question_number) + " has been removed.")
    except WrongPeriodException:
        await interaction.response.send_message("The competition is underway, so you cannot add or remove questions.")


@tree.command(name="change_contest_period",
              description="[Mod Only] Changes the period of a contest.",
              guild=GUILD)
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
@discord.app_commands.choices(period_name=[
    discord.app_commands.Choice(name='pre-signup', value='pre-signup'),
    discord.app_commands.Choice(name='signup', value='signup'),
    discord.app_commands.Choice(name='competition', value='competition'),
    discord.app_commands.Choice(name='post-competition', value='post-competition')
])
@discord.app_commands.checks.has_any_role('Olympiad Team', 'Olympiad Manager')
async def change_contest_period(interaction, contest_name: str, period_name: str):
    match period_name.lower():
        case 'pre-signup':
            period = ContestPeriod.preSignup
        case 'signup':
            period = ContestPeriod.signup
        case 'competition':
            period = ContestPeriod.competition
        case 'post-competition':
            period = ContestPeriod.postCompetition
        case _:
            await interaction.response.send_message("An invalid period name has been entered.", ephemeral=True)
            return
    contest = Contest.from_json(contest_name)
    contest.period = period
    contest.update_json()
    await interaction.response.send_message(f"Success! The contest period has been changed to {period_name}.")


@tree.command(name="contest_period",
              description="Gives info about the current phase of the contest.",
              guild=GUILD)
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
async def contest_period(interaction, contest_name: str):
    contest = Contest.from_json(contest_name)
    match contest.period:
        case ContestPeriod.preSignup:
            message = "The current period of the contest is pre-signup. In this phase, you cannot register teams."
        case ContestPeriod.signup:
            message = ("The current period of the contest is signup. Now, you can create and join teams; but you "
                       "cannot answer questions yet.")
        case ContestPeriod.competition:
            message = ("The current period of the contest is competition. Here, you can answer questions ande join "
                       "existing teams; but no new teams can be created.")
        case ContestPeriod.postCompetition:
            message = ("The current period of the contest is post-competition. At this point, the contest is already "
                       "finished; and results are out. No answers can be submitted.")
        case _:
            message = "Unknown period...Ask Daniel to update the contest_period command."
    await interaction.response.send_message(message)


@tree.command(name="create_contest_channels",
              description="[Mod Only] Creates the private channels for all of the teams.",
              guild=GUILD)
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
@discord.app_commands.checks.has_any_role('Olympiad Team', 'Olympiad Manager')
async def create_contest_channels(interaction, contest_name: str, channel_category: discord.CategoryChannel):
    contest = Contest.from_json(contest_name)
    manager_role = discord.utils.get(interaction.guild.roles, name="Olympiad Team")
    admin_role = discord.utils.get(interaction.guild.roles, name="Olympiad Manager")
    for team in contest.teams:
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            manager_role: discord.PermissionOverwrite(read_messages=True),
            admin_role: discord.PermissionOverwrite(read_messages=True),
            interaction.guild.get_member(team.owner_id): discord.PermissionOverwrite(read_messages=True)
        }
        for member_id in team.member_ids:
            overwrites[interaction.guild.get_member(member_id)] = discord.PermissionOverwrite(read_messages=True)
        channel = await interaction.guild.create_text_channel(
            team.name + '-contest-channel',
            overwrites=overwrites,
            category=channel_category)
        team.channel_id = channel.id
        contest.update_json()
    await interaction.response.send_message("Channels have been opened!.")


# untested.
@tree.command(name="delete_contest_channels",
              description="[Mod Only; DANGER ZONE] Deletes all of the contest channels.",
              guild=GUILD)
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
@discord.app_commands.checks.has_any_role('Olympiad Team', 'Olympiad Manager')
async def delete_contest_channels(interaction, contest_name: str):
    contest = Contest.from_json(contest_name)
    for team in contest.teams:
        if team.channel_id:
            await interaction.guild.get_channel(team.channel_id).delete()
    await interaction.response.send_message("All contest channels deleted!.")


@tree.command(name="answer_question",
              description="Answer a question within a specific contest.",
              guild=GUILD)
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
async def answer_question(interaction, contest_name: str, question_number: int, answer: float):
    try:
        contest = Contest.from_json(contest_name)
        user_team = contest.get_team_of_user(interaction.user.id)
        if user_team:
            user_team.answer(contest.get_question(question_number), answer)
        else:
            await interaction.response.send_message(
                "Hmmm..... your team doesn't seem to be found in the contest. Maybe you haven't signed up yet?",
                ephemeral=True)
        contest.update_json()
        await interaction.response.send_message(
            str(interaction.user) + f" has answered question {question_number}!")
    except AnswersAlreadySubmittedException:
        await interaction.response.send_message(
            "Sorry, you have already submitted your answers. Once you submit your answers, you cannot answer anything "
            "else.",
            ephemeral=True)
    except WrongPeriodException:
        await interaction.response.send_message(
            "Sorry, you can't submit any answers right now, as the contest period is not the competition period.",
            ephemeral=True)
    except IndexError:
        await interaction.response.send_message(
            "Sorry, but the contest doesn't have a problem with number " + str(question_number))


@tree.command(name="submit_all_answers",
              description="Submits your teams' answers. Once you submit, you CANNOT unsubmit!",
              guild=GUILD)
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
async def submit_team_answers(interaction, contest_name: str):
    try:
        contest = Contest.from_json(contest_name)
        player_team = contest.get_team_of_user(interaction.user.id)
        if player_team and player_team.owner_id == interaction.user.id:
            player_team.submit_answers()
            contest.update_json()
            await interaction.response.send_message("The owner has officially submitted all of their teams' answers!")
        else:
            await interaction.response.send_message(
                "Sorry, you are not the owner, and thus you cannot submit any answers.")
    except WrongPeriodException:
        await interaction.response.send_message(
            "Sorry, but you cannot submit any answers right now, as the contest is not in the competition period.")


@tree.command(name="show_questions_with_answers",
              description="[Mod Only] Gets the answer and point value of all questions within the specified contest.",
              guild=GUILD)
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
@discord.app_commands.checks.has_any_role('Olympiad Team', 'Olympiad Manager')
async def show_questions_with_answers(interaction, contest_name: str):
    contest = Contest.from_json(contest_name)
    question_string = ""
    for question in contest.questions:
        question_string += (f"Question {question.number}: answer = {question.correct_answer}, "
                            f"points = {question.point_value} \n")
    if question_string == "":
        await interaction.response.send_message(
            "Hmm... There doesn't seem to be any questions in the contest currently. To add one, use /add_question.")
    else:
        await interaction.response.send_message(question_string)


@tree.command(name="link",
              description="Gets the link of a contest.",
              guild=GUILD)
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
async def link(interaction, contest_name: str):
    contest = Contest.from_json(contest_name)
    if contest.period == ContestPeriod.competition or contest.period == ContestPeriod.postCompetition:
        await interaction.response.send_message(contest.link, ephemeral=True)
    else:
        await interaction.response.send_message("Sorry, you cannot access this right now.", ephemeral=True)


@tree.command(name="change_link",
              description="[Mod Only] Changes the link of a contest.",
              guild=GUILD)
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
@discord.app_commands.checks.has_any_role('Olympiad Team', 'Olympiad Manager')
async def change_link(interaction, contest_name: str, new_link: str):
    contest = Contest.from_json(contest_name)
    contest.link = new_link
    contest.update_json()
    await interaction.response.send_message("Link has been changed!")


@tree.command(name="team_rankings",
              description="Gets the team rankings for the specified contest.",
              guild=GUILD)
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
async def team_rankings(interaction, contest_name: str):
    try:
        contest = Contest.from_json(contest_name)
        rankings: list[str] = []
        rank = 1
        for team in contest.team_rankings:
            rankings.append(f"Rank {rank}: {team.name}, total points = {team.total_points}.")
            rank += 1
        await interaction.response.send_message("\n".join(rankings))
    except WrongPeriodException:
        await interaction.response.send_message(
            "The competition hasn't started yet, and thus there aren't any rankings. "
            "Use /all_teams instead to get a list of every team.")


@tree.command(name="show_teams",
              description="Shows all teams, and their members, within a contest.",
              guild=GUILD)
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
async def show_teams(interaction, contest_name: str):
    contest = Contest.from_json(contest_name)
    team_blurbs: list[str] = []
    for team in contest.teams:
        team_blurbs.append(f"Team '{team.name}', with owner '{get_member_repr(interaction, team.owner_id)}' and members"
                           f" {[get_member_repr(interaction, member_id) for member_id in team.member_ids]},")
    await interaction.response.send_message("All teams: \n" + "\n".join(team_blurbs))


@tree.command(name="show_questions",
              description="Shows the questions of a contest with their respective point value. Does not show answers.",
              guild=GUILD)
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
async def show_questions(interaction, contest_name: str):
    contest = Contest.from_json(contest_name)
    questions_strings: list[str] = []
    for question in contest.questions:
        questions_strings.append(f"Question {question.number}: points = {question.point_value}")
    if len(questions_strings) == 0:
        await interaction.response.send_message(
            "There are no questions at the moment. The contest might still be in it's signup phase.", ephemeral=True)
    else:
        await interaction.response.send_message("All questions: \n" + "\n".join(questions_strings))


@tree.command(name="delete_contest",
              description="[Mod Only; DANGER ZONE] Deletes a contest.",
              guild=GUILD)
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
@discord.app_commands.checks.has_any_role('Olympiad Team', 'Olympiad Manager')
async def delete_contest(interaction, contest_name: str):
    Contest.delete_json(contest_name)
    await interaction.response.send_message("Contest has been deleted!")


@tree.command(name="remove_member_from_team",
              description="[Mod Only] Removes a member from a team.",
              guild=GUILD)
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion, team_name=all_team_names_autocompletion)
@discord.app_commands.checks.has_any_role('Olympiad Team', 'Olympiad Manager')
async def remove_member_from_team(interaction, contest_name: str, team_name: str, member: discord.Member):
    contest: Contest = Contest.from_json(contest_name)
    team = contest.get_team(team_name)
    try:
        team.remove_member(member.id)
    except OwnerLeaveTeamException:
        await interaction.user.send_message(
            "You cannot remove an owner. Use /force_transfer_ownership to transfer ownership to someone else.",
            ephemeral=True)
    except MemberNotInTeamException:
        await interaction.user.send_message("This member is not currently in the team.", ephemeral=True)
    finally:
        contest.update_json()


@tree.command(name="unsubmit_answers_of_team",
              description="[Mod Only] Unsubmits a team's answers.",
              guild=GUILD)
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion, team_name=all_team_names_autocompletion)
@discord.app_commands.checks.has_any_role('Olympiad Team', 'Olympiad Manager')
async def unsubmit_answers_of_team(interaction, contest_name: str, team_name: str):
    contest: Contest = Contest.from_json(contest_name)
    team: Team = contest.get_team(team_name)
    team.answers_submitted = False
    team.submit_ranking = 0
    contest.update_json()
    await interaction.response.send_message("Success!")


@tree.command(name="transfer_ownership_of_team",
              description="[Mod Only] Forces team ownership transfer.",
              guild=GUILD)
@discord.app_commands.checks.has_any_role('Olympiad Team', 'Olympiad Manager')
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion, team_name=all_team_names_autocompletion)
async def transfer_ownership_of_team(interaction, contest_name: str, team_name: str, new_owner: discord.Member):
    try:
        contest = Contest.from_json(contest_name)
        player_team = contest.get_team(team_name)
        if player_team is None:
            await interaction.response.send_message("Hmmm... this team cannot be found", ephemeral=True)
        else:
            player_team.transfer_ownership(new_owner.id)
            contest.update_json()
            await interaction.response.send_message(f"Ownership has been successfully transferred to {new_owner}!")
    except MemberNotInTeamException:
        await interaction.response.send_message(
            "The member that you tried to transfer ownership in is not in the team(or hasn't accepted the invite yet).",
            ephemeral=True)


@tree.command(name="add_member_to_team",
              description="[Mod Only] Forcefully adds a member to a team.",
              guild=GUILD)
@discord.app_commands.checks.has_any_role('Olympiad Team', 'Olympiad Manager')
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion, team_name=all_team_names_autocompletion)
async def add_member_to_team(interaction, contest_name: str, team_name: str, new_member: discord.Member):
    contest = Contest.from_json(contest_name)
    team = contest.get_team(team_name)
    try:
        team.register_member(new_member.id, ignore_invite=True)
        contest.update_json()
        await interaction.response.send_message("Success!")
    except MemberInAnotherTeamException:
        await interaction.response.send_message("This member is already in another team.", ephemeral=True)
    except TeamSizeExceededException:
        await interaction.response.send_message(
            f"The team size limit of {contest.team_size_limit} has been exceeded.", ephemeral=True)


@tree.command(name="submit_answers_for_team",
              description="[Mod Only] Forcefully submits answers for teams who haven't submitted yet.",
              guild=GUILD)
@discord.app_commands.checks.has_any_role('Olympiad Team', 'Olympiad Manager')
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
async def submit_answers_for_team(interaction, contest_name: str):
    try:
        contest = Contest.from_json(contest_name)
        for team in contest.teams:
            if not team.answers_submitted:
                team.submit_answers()
        contest.update_json()
        await interaction.response.send_message("Success!")
    except WrongPeriodException:
        await interaction.response.send_message(
            "The period must be ContestPeriod.Competition for this to work.", ephemeral=True)


@tree.command(name="answer_question_for_team",
              description="[Mod Only] Forcefully answers a question for a team.",
              guild=GUILD)
@discord.app_commands.checks.has_any_role('Olympiad Team', 'Olympiad Manager')
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion, team_name=all_team_names_autocompletion)
async def answer_question_for_team(interaction, contest_name: str, team_name: str, question_number: int, answer: float):
    try:
        contest = Contest.from_json(contest_name)
        team = contest.get_team(team_name)
        team.answer(contest.get_question(question_number), answer)
        contest.update_json()
        await interaction.response.send_message(f"Question {question_number} for team {team_name} was answered.")
    except AnswersAlreadySubmittedException:
        await interaction.response.send_message("Hmm... this team has already submitted their answers.", ephemeral=True)
    except WrongPeriodException:
        await interaction.response.send_message(
            "Sorry, you can't submit any answers right now, as the contest period is not the competition period.",
            ephemeral=True)
    except IndexError:
        await interaction.response.send_message(
            "Sorry, but the contest doesn't have a problem with number " + str(question_number), ephemeral=True)


@tree.command(name="show_answers",
              description="Your team's current answers(not necessarily the correct ones!)",
              guild=GUILD)
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
async def answered_questions(interaction, contest_name: str):
    contest = Contest.from_json(contest_name)
    team = contest.get_team_of_user(interaction.user.id)
    if team:
        await interaction.response.send_message(team.answering_status())
    else:
        await interaction.response.send_message("Hmmm... your team could not be found.")


@tree.command(name="show_answers_of_team",
              description="[Mod Only] What a certain team has answered; includes grading.",
              guild=GUILD)
@discord.app_commands.checks.has_any_role('Olympiad Team', 'Olympiad Manager')
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion, team_name=all_team_names_autocompletion)
async def answered_questions_admin(interaction, contest_name: str, team_name: str):
    contest = Contest.from_json(contest_name)
    team = contest.get_team(team_name)
    if team:
        await interaction.response.send_message(team.answering_status(display_correct_answer=True))
    else:
        await interaction.response.send_message("Hmmm... the team could not be found.")


@tree.command(name="change_contest_name",
              description="[Mod Only] Changes the name of an existing contest.",
              guild=GUILD)
@discord.app_commands.checks.has_any_role('Olympiad Team', 'Olympiad Manager')
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
async def change_contest_name(interaction, contest_name: str, new_name: str):
    contest = Contest.from_json(contest_name)
    contest.name = new_name
    contest.update_json()
    Contest.delete_json(contest_name)
    await interaction.response.send_message(f"Success! The name has been changed to {contest_name}")


@tree.command(name="sync",
              description="[Mod Only] Syncs the current slash commands.",
              guild=GUILD)
@discord.app_commands.checks.has_any_role('Olympiad Team', 'Olympiad Manager')
async def sync_bot_commands(interaction):
    await interaction.response.defer(thinking=True)
    await tree.sync(guild=GUILD)
    await interaction.followup.send("Commands synced.")


@tree.command(name="sync_global",
              description="[Mod Only] Syncs slash command on all servers.")
@discord.app_commands.checks.has_any_role('Olympiad Team', 'Olympiad Manager')
async def sync_commands_globally(interaction):
    await interaction.response.defer(thinking=True)
    await tree.sync()
    await interaction.followup.send("Commands synced across all guilds.")


# DO NOT DELETE THESE LINES OF CODE:
# tree.add_command(db_group)
client.run(os.environ['token'])
