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
    WrongPeriodException, DataAPIException
)

import traceback
import logging
from dotenv import load_dotenv
load_dotenv("secrets.env")


intents = discord.Intents.default()
intents.members = True
client: discord.Client = discord.Client(intents=intents)
tree: discord.app_commands.CommandTree = discord.app_commands.CommandTree(client)

# important!
current_guild_id: int = int(os.environ["current_guild_id"])
guild_category_name = "DSMC 2024"


async def contest_name_autocompletion(interaction, current: str) -> list:
    data = []
    for contest_name in Contest.all_names():
        data.append(discord.app_commands.Choice(name=contest_name.lower(), value=contest_name))
    return data


async def team_name_autocompletion(interaction, current: str):
    contest_name = interaction.namespace.contest_name
    contest = Contest.from_json(contest_name)
    team_name_choices = []
    for team in contest.all_teams:
        if interaction.user.id in team.invited_member_ids or interaction.user.id == team.owner_id:
            team_name_choices.append(discord.app_commands.Choice(name=team.name.lower(), value=team.name))
    return team_name_choices


async def all_team_names_autocompletion(interaction, current: str):
    contest = Contest.from_json(interaction.namespace.contest_name)
    team_name_choices: list[discord.app_commands.Choice] = []
    for team in contest.all_teams:
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
    # await tree.sync()
    print("Ready!")


@tree.error
async def on_app_command_error(interaction, error):
    if isinstance(error.original, DataAPIException):
        await interaction.response.send_message(
            "A data API issue has just occured. This could be a typo, or a problem with the bot. "
            "Please consult one of the test proctors and/or @DanielRocksUrMom for help. ")
    else:
        await interaction.response.send_message(
            "Sorry, there was a problem with the bot, so an uncaught error has occurred. "
            "Please consult @DanielRocksUrMom for help.")
    daniel = client.get_user(614549755342880778)
    if daniel is not None:
        channel = await daniel.create_dm()
        await channel.send("Hey Daniel, the user '{errorCauserName}' just caused an error in your code.'".format(
            errorCauserName=interaction.user.name))
        error = traceback.format_exc()
        with open('errors.log', 'a+') as file:
            file.write(error)
            await channel.send("This is the error file: ", file=discord.File(file, "errors.log"))
    else:
        print("Failed to write to disk.")
    logging.warning(error)


@tree.command(name="create_contest", 
              description="MOD ONLY. Creates a new Contest.",
              guild=discord.Object(id=current_guild_id))  
@discord.app_commands.checks.has_any_role('Olympiad Team', 'Olympiad Manager')
async def create_contest(interaction, name: str, link: str, team_size_limit: int | None = None,
                         total_teams_limit: int | None = None):
    Contest(name.lower(), link, team_size_limit, total_teams_limit).update_json()
    await interaction.response.send_message("Contest successfully created!")


@tree.command(name="all_contest_competitors", 
              description="Displays all contest competitors",
              guild=discord.Object(id=current_guild_id))  
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
async def all_contest_competitors(interaction, contest_name: str):
    contest = Contest.from_json(contest_name)
    all_participants = [get_member_repr(interaction, member_id) for member_id in contest.all_contest_participants]
    all_invited_participants = [get_member_repr(interaction, member_id) for member_id in contest.all_invited_members]
    await interaction.response.send_message("These people are currently in a team: \n" + str(
        all_participants) + "\n These people are currently invited to a team: " + str(all_invited_participants))


@tree.command(name="register_team", 
              description="Registers a team into a contest. ",
              guild=discord.Object(id=current_guild_id))  
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
async def register_team(interaction, contest_name: str, team_name: str, member_two: discord.Member | None = None,
                        member_three: discord.Member | None = None, member_four: discord.Member | None = None):
    invite_list: list[discord.Member] = []
    if member_two is not None:
        invite_list.append(member_two)
    if member_three is not None:
        invite_list.append(member_three)
    if member_four is not None:
        invite_list.append(member_four)

    contest = Contest.from_json(contest_name)
    try:
        new_team = Team(
            contest_instance=contest,
            name=team_name,
            owner_id=interaction.user.id,
            invited_member_ids=[member.id for member in invite_list]
        )
        contest.add_team(new_team)
        print(new_team.get_data())
        await interaction.response.send_message(
            "Team '{teamName}' has been added to the contest with the users {members} invited. "
            "In order for them to join your team, they must use /join_team {teamName}."
            .format(members=[member.display_name for member in invite_list], teamName=team_name))
        for member in invite_list:
            channel = await member.create_dm()
            await channel.send(
                "The user {user} has invited you to join the team '{team_name}' for the contest '{contest_name}'. "
                "In order to join, use '/join_team {team_name}' in the Mathematics Server (it doesn't work within DMs)."
                "If you don't want to join, ignore this message."
                .format(user=interaction.user, contest_name=contest.name, team_name=team_name))
        contest.update_json()
    except WrongPeriodException:
        await interaction.response.send_message(
            "You can only create a team when this contest is in it's signup phase. Sorry!")
    except MemberInAnotherTeamException:
        await interaction.response.send_message(
            "You seem to be in another team as of now. The team that you currently are in is {teamName}.".format(
                teamName=contest.get_team_of_user(interaction.user.id)))


@tree.command(name="invite_more_members", 
              description="Invites more members to your team",
              guild=discord.Object(id=current_guild_id))  
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
async def invite_more_members(interaction, contest_name: str, member_one: discord.Member | None = None,
                              member_two: discord.Member | None = None, member_three: discord.Member | None = None):
    contest = Contest.from_json(contest_name)
    message = ""
    user_team = contest.get_team_of_user(interaction.user.id)
    if user_team is None:
        await interaction.response.send_message("Hmmm... It looks like you are not in a team yet.")
        return
    if member_one is not None:
        user_team.invite_member(member_one.id)
        message += "{memberName} has been successfully added. \n".format(memberName=member_one.name)
    if member_two is not None:
        user_team.invite_member(member_two.id)
        message += "{memberName} has been successfully added. \n".format(memberName=member_two.name)
    if member_three is not None:
        user_team.invite_member(member_three.id)
        message += "{memberName} has been successfully added. \n".format(memberName=member_three.name)
    contest.update_json()
    await interaction.response.send_message(message)


@tree.command(name="join_team", 
              description="Join one of the teams you were invited to.",
              guild=discord.Object(id=current_guild_id))  
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion, team_name=team_name_autocompletion)
async def join_team(interaction, contest_name: str, team_name: str):
    contest = Contest.from_json(contest_name)
    new_team = contest.get_team(team_name)
    if interaction.user.id in new_team.member_ids or interaction.user.id == new_team.owner_id:
        await interaction.response.send_message(
            "Looks like you are already in this team. To leave, use /leave_current_team.", 
            ephemeral=True)
        return
    try:
        new_team.add_member(interaction.user.id)
        await interaction.response.send_message(
            "Hooray! You have officially joined team {teamName}! to leave, use /leave_current_team."
            .format(teamName=team_name))
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


@tree.command(name="change_team_name", 
              description="Change the name of the team you are in.",
              guild=discord.Object(id=current_guild_id))  
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
async def change_team_name(interaction, contest_name: str, new_team_name: str):
    contest = Contest.from_json(contest_name)
    team = contest.get_team_of_user(interaction.user.id)
    if team is not None:
        previous_name = team.name
        team.name = new_team_name
        contest.update_json()
        await interaction.response.send_message(
            "The team that was previously refferred to as '" +
            previous_name + "' now has the name '" + team.name + "'."
        )
    else:
        await interaction.response.send_message("It seems that you are not in a team currently.", ephemeral=True)


@tree.command(name="modify_team_size_limit", 
              description="MOD ONLY. Modifies the team size limit for a contest. ",
              guild=discord.Object(id=current_guild_id))  
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
@discord.app_commands.checks.has_any_role('Olympiad Team', 'Olympiad Manager')
async def modify_team_size_limit(interaction, contest_name: str, size_limit: int):
    contest = Contest.from_json(contest_name)
    contest.team_size_limit = size_limit
    contest.update_json()
    await interaction.response.send_message("Team size limit has been updated to " + str(size_limit) + ".")


@tree.command(name="modify_total_teams_limit", 
              description="MOD ONLY. Modifies the total teams limit for a contest. ",
              guild=discord.Object(id=current_guild_id))  
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
@discord.app_commands.checks.has_any_role('Olympiad Team', 'Olympiad Manager')
async def modify_total_teams_limit(interaction, contest_name: str, teams_limit: int):
    contest = Contest.from_json(contest_name)
    contest.total_teams_limit = teams_limit
    contest.update_json()
    await interaction.response.send_message("Total teams limit has been updated to " + str(teams_limit) + ".")


@tree.command(name="leave_current_team", 
              description="Leaves your current team in the respective contest.",
              guild=discord.Object(id=current_guild_id))  
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
              guild=discord.Object(id=current_guild_id))  
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
            await interaction.response.send_message(
                "Ownership has been successfully transferred to {newOwner}!".format(newOwner=new_owner))
        else:
            await interaction.response.send_message(
                "Sorry, you're not the owner of the team you're in, so you cannot transfer ownership.", ephemeral=True)
    except MemberNotInTeamException:
        await interaction.response.send_message(
            "The member that you tried to transfer ownership in is not in the team(or hasn't accepted the invite yet).")


@tree.command(name="unregister_team", 
              description="Unregisters your team ",
              guild=discord.Object(id=current_guild_id))  
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
                "The original owner of team {teamName} has deleted this team. "
                "To sign up for another team, ask another team owner to invite you, then use /join."
                .format(teamName=user_team.name))
        await interaction.response.send_message("Success!")
        contest.update_json()


@tree.command(name="add_question", 
              description="MOD ONLY. Adds a question into a contest. Mods only!",
              guild=discord.Object(id=current_guild_id))  
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


@tree.command(name="remove_question", description="MOD ONLY. Removes a question from a specified contest.",
              guild=discord.Object(id=current_guild_id))  
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
              description="MOD ONLY. changes the period of a contest.",
              guild=discord.Object(id=current_guild_id))  
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
@discord.app_commands.choices(period_name=[
    discord.app_commands.Choice(name='pre-signup', value='pre-signup'),
    discord.app_commands.Choice(name='signup', value='signup'),
    discord.app_commands.Choice(name='competition', value='competition'),
    discord.app_commands.Choice(name='post-competition', value='post-competition')
])
@discord.app_commands.checks.has_any_role('Olympiad Team', 'Olympiad Manager')
async def change_contest_period(interaction, contest_name: str, period_name: str):
    if period_name == 'pre-signup':
        period = ContestPeriod.preSignup
    elif period_name == 'signup':
        period = ContestPeriod.signup
    elif period_name == 'competition':
        period = ContestPeriod.competition
    elif period_name == 'post-competition':
        period = ContestPeriod.postCompetition
    else:
        raise Exception("An invalid string " + period_name + " was passed.")

    contest = Contest.from_json(contest_name)
    contest.period = period
    contest.update_json()
    await interaction.response.send_message("Success! The contest period has been changed to " + str(period))


@tree.command(name="create_contest_channels",
              description="MOD ONLY. Creates the private channels for all of the teams.",
              guild=discord.Object(id=current_guild_id))  
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
@discord.app_commands.checks.has_any_role('Olympiad Team', 'Olympiad Manager')
async def create_contest_channels(interaction, contest_name: str):
    contest = Contest.from_json(contest_name)
    for team in contest.all_teams:
        manager_role = discord.utils.get(interaction.guild.roles, name="Olympiad Team")
        admin_role = discord.utils.get(interaction.guild.roles, name="Olympiad Manager")
        try:
            category = discord.utils.get(interaction.guild.categories, name=guild_category_name)
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
                category=category)
            contest.channel_id_info[team.name] = channel.id
            contest.update_json()
        except:
            await interaction.response.send_message(
                "Hmmm.... It looks like this server doesn't have a category named '"
                + guild_category_name + "'. Try again.")
            return
    await interaction.response.send_message("Channels have been opened!.")


# untested.
@tree.command(name="delete_contest_channels", 
              description="MOD ONLY. Deletes all of the contest channels",
              guild=discord.Object(id=current_guild_id))  
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
@discord.app_commands.checks.has_any_role('Olympiad Team', 'Olympiad Manager')
async def delete_contest_channels(interaction, contest_name: str):
    contest = Contest.from_json(contest_name)
    for team in contest.all_teams:
        await interaction.guild.get_channel(contest.channel_id_info[team.name]).delete()
    await interaction.response.send_message("All contest channels deleted!.")


@tree.command(name="answer_question", 
              description="answer a question on a specific test",
              guild=discord.Object(id=current_guild_id))  
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
async def answer_question(interaction, contest_name: str, question_number: int, answer: float):
    try:
        contest = Contest.from_json(contest_name)
        user_team = contest.get_team_of_user(interaction.user.id)
        if user_team is not None:
            user_team.answer(contest.get_question(question_number), answer)
        else:
            await interaction.response.send_message(
                "Hmmm..... your team doesn't seem to be found in the contest. Maybe you haven't signed up yet?",
                ephemeral=True)
        contest.update_json()
        await interaction.response.send_message(
            str(interaction.user) + " has answered question #{question_number}!".format(
                question_number=question_number))
    except AnswersAlreadySubmittedException:
        await interaction.response.send_message(
            "Sorry, you have already submitted your answers. Once you submit your answers, you cannot answer anything else.",
            ephemeral=True)
    except WrongPeriodException:
        await interaction.response.send_message(
            "Sorry, you can't submit any answers right now, as the contest period is not the competition period.",
            ephemeral=True)
    except:
        await interaction.response.send_message(
            "Sorry, but the contest doesn't have a problem with number " + str(question_number))


@tree.command(name="submit_all_answers",
              description="Submits your teams' answers. Once you submit, you CANNOT unsubmit!",
              guild=discord.Object(id=current_guild_id))  
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
async def submit_team_answers(interaction, contest_name: str):
    try:
        contest = Contest.from_json(contest_name)
        player_team = contest.get_team_of_user(interaction.user.id)
        if player_team is not None and player_team.owner_id == interaction.user.id:
            player_team.submit_answers()
            contest.update_json()
            await interaction.response.send_message("The owner has officially submitted all of their teams' answers!")
        else:
            await interaction.response.send_message(
                "Sorry, you are not the owner, and thus you cannot submit any answers.")
    except WrongPeriodException:
        await interaction.response.send_message(
            "Sorry, but you cannot submit any answers right now, as the contest is not in the competition period.")


@tree.command(name="question_answer_score",
              description="MOD ONLY. Gets the answer and point value of all questions within the specified contest.",
              guild=discord.Object(id=current_guild_id))  
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
@discord.app_commands.checks.has_any_role('Olympiad Team', 'Olympiad Manager')
async def question_answer_score(interaction, contest_name: str):
    contest = Contest.from_json(contest_name)
    question_string = ""
    for question in contest.all_questions:
        question_string += "Q{questionNumber}: answer = {answer}, points = {pointValue} \n".format(
            questionNumber=question.get_number(), answer=question.correct_answer, pointValue=question.point_value)
    if question_string == "":
        await interaction.response.send_message(
            "Hmm... There doesn't seem to be any questions in the contest currently. To add one, use /add_question.")
    else:
        await interaction.response.send_message(question_string)


@tree.command(name="link", description="gets the link of a contest.",
              guild=discord.Object(id=current_guild_id))  
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
async def link(interaction, contest_name: str):
    contest = Contest.from_json(contest_name)
    if contest.period == ContestPeriod.competition or contest.period == ContestPeriod.postCompetition:
        await interaction.response.send_message(contest.link, ephemeral=True)
    else:
        await interaction.response.send_message("Sorry, you cannot access this right now.", ephemeral=True)


@tree.command(name="change_link", description="MOD ONLY. changes the link of a contest.",
              guild=discord.Object(id=current_guild_id))  
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
@discord.app_commands.checks.has_any_role('Olympiad Team', 'Olympiad Manager')
async def change_link(interaction, contest_name: str, new_link: str):
    contest = Contest.from_json(contest_name)
    contest.link = new_link
    contest.update_json()
    await interaction.response.send_message("Link has been changed!")


@tree.command(name="team_rankings", description="get the team rankings for the specified contest.",
              guild=discord.Object(id=current_guild_id))  
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
async def team_rankings(interaction, contest_name: str):
    try:
        contest = Contest.from_json(contest_name)
        rankingString = ""
        counter = 1
        for team in contest.team_rankings:
            rankingString += "#{rank}: {teamName}, with {points} points. \n".format(rank=counter, teamName=team.name,
                                                                                    points=team.total_points)
            counter += 1
        try:
            await interaction.response.send_message(rankingString)
        except:
            await interaction.response.send_message(
                "Oops... Looks like there isn't any teams left in this competition. "
                "Hopefully, this is a glitch (everybody leaving DSMC would be really sadge).")
    except WrongPeriodException:
        await interaction.response.send_message(
            "The competition hasn't started yet, and thus there aren't any rankings. "
            "Use /all_teams instead to get a list of every team.")


@tree.command(name="all_teams", description="shows all teams, as well as which members are in each team.",
              guild=discord.Object(id=current_guild_id))  
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
async def all_teams(interaction, contest_name: str):
    contest = Contest.from_json(contest_name)
    all_teams_string = ""
    for team in contest.all_teams:
        all_teams_string += "Team '{teamName}', with owner '{owner}' and members {members}, \n".format(
            teamName=team.name,
            owner=get_member_repr(interaction, team.owner_id),
            members=[get_member_repr(interaction, member_id) for member_id in team.member_ids]
        )
    await interaction.response.send_message("All teams: \n" + all_teams_string)


@tree.command(name="question_info",
              description="Shows all the questions of a specific contest. Does not show the answers and/or points.",
              guild=discord.Object(id=current_guild_id))  
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
async def question_info(interaction, contest_name: str):
    contest = Contest.from_json(contest_name)
    all_questions_string = ""
    for question in contest.all_questions:
        all_questions_string += "Q" + str(question.get_number())
        all_questions_string += ": Point Value " + str(question.point_value) + " \n"
    if all_questions_string == "":
        await interaction.response.send_message(
            "There is no questions at the moment. The contest might still be in maintenance/signup mode.")
    else:
        await interaction.response.send_message("All questions: \n" + all_questions_string)


@tree.command(name="delete_contest", description="MOD ONLY. deletes a contest. WARNING - avoid using this command.",
              guild=discord.Object(id=current_guild_id))  
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
@discord.app_commands.checks.has_any_role('Olympiad Team', 'Olympiad Manager')
async def delete_contest(interaction, contest_name: str):
    Contest.delete_json(contest_name)
    await interaction.response.send_message("Contest has been deleted!")


@tree.command(name="remove_member_from_team", description="MOD ONLY. Removes a member from a team.",
              guild=discord.Object(id=current_guild_id))  
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion, team_name=all_team_names_autocompletion)
@discord.app_commands.checks.has_any_role('Olympiad Team', 'Olympiad Manager')
async def remove_member_from_team(interaction, contest_name: str, team_name: str, member: discord.Member):
    contest: Contest = Contest.from_json(contest_name)
    team = contest.get_team(team_name)
    try:
        team.remove_member(member.id)
    except OwnerLeaveTeamException:
        try:
            team.transfer_ownership(team.member_ids[0])
            await interaction.user.send_message(
                "The member you tried to remove was an owner; thus, the owner is now a random member within the team.",
                ephemeral=True
            )
            team.remove_member(member.id)
        except IndexError:
            await interaction.user.send_message(
                "There is no other members to transfer ownership to. Use delete_team instead.",
                ephemeral=True
            )
    except MemberNotInTeamException:
        await interaction.user.send_message("This member is not currently in the team.", ephemeral=True)
    finally:
        contest.update_json()


@tree.command(name="unsubmit_team_answers", description="MOD ONLY- unsubmits team answers in an emergency scenario",
              guild=discord.Object(id=current_guild_id))  
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion, team_name=all_team_names_autocompletion)
@discord.app_commands.checks.has_any_role('Olympiad Team', 'Olympiad Manager')
async def unsubmit_team_answers(interaction, contest_name: str, team_name: str):
    contest: Contest = Contest.from_json(contest_name)
    team: Team = contest.get_team(team_name)
    team.answers_submitted = False
    team.submit_ranking = 0
    contest.update_json()
    await interaction.response.send_message("Success!")


@tree.command(name="force_transfer_ownership",
              description="[Bot administrators only; forces team ownership transfer.]")  
@discord.app_commands.checks.has_any_role('Olympiad Team', 'Olympiad Manager')
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion, team_name=all_team_names_autocompletion)
async def force_transfer_ownership(interaction, contest_name: str, team_name: str, new_owner: discord.Member):
    try:
        contest = Contest.from_json(contest_name)
        player_team = contest.get_team(team_name)
        if player_team is None:
            await interaction.response.send_message("Hmmm... this team cannot be found", ephemeral=True)
        else:
            player_team.transfer_ownership(new_owner.id)
            contest.update_json()
            await interaction.response.send_message(
                "Ownership has been successfully transferred to {newOwner}!".format(newOwner=new_owner))
    except MemberNotInTeamException:
        await interaction.response.send_message(
            "The member that you tried to transfer ownership in is not in the team(or hasn't accepted the invite yet).")


@tree.command(name="force_add_members",
              description="[Bot administrators only; adds members forcefully to a team.]")  
@discord.app_commands.checks.has_any_role('Olympiad Team', 'Olympiad Manager')
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion, team_name=all_team_names_autocompletion)
async def force_add_members(interaction, contest_name: str, team_name: str, new_member: discord.Member):
    contest = Contest.from_json(contest_name)
    team = contest.get_team(team_name)
    team.member_ids.append(new_member.id)
    contest.update_json()
    await interaction.response.send_message("Success!")


@tree.command(name="force_answer_submissions",
              description="[Bot administrators only; forcefully submits answers for teams who haven't submitted yet.]")
@discord.app_commands.checks.has_any_role('Olympiad Team', 'Olympiad Manager')
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
async def force_team_submissions(interaction, contest_name: str):
    try:
        contest = Contest.from_json(contest_name)
        for team in contest.all_teams:
            if not team.answers_submitted:
                team.submit_answers()
        contest.update_json()
        await interaction.response.send_message("Success!")
    except WrongPeriodException:
        await interaction.response.send_message("The period must be ContestPeriod.Competition for this to work.")


@tree.command(name="answer_question_for_team",
              description="[Bot administrators only]")
@discord.app_commands.checks.has_any_role('Olympiad Team', 'Olympiad Manager')
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion, team_name=all_team_names_autocompletion)
async def answer_question_for_team(interaction, contest_name: str, team_name: str, question_number: int, answer: float):
    try:
        contest = Contest.from_json(contest_name)
        team = contest.get_team(team_name)
        team.answer(contest.get_question(question_number), answer)
        contest.update_json()
        await interaction.response.send_message(
            "An admin has answered question #{question_number}!".format(question_number=question_number))
    except AnswersAlreadySubmittedException:
        await interaction.response.send_message("Hmm... this team has already submitted their answers.", ephemeral=True)
    except WrongPeriodException:
        await interaction.response.send_message(
            "Sorry, you can't submit any answers right now, as the contest period is not the competition period.",
            ephemeral=True)
    except IndexError:
        await interaction.response.send_message(
            "Sorry, but the contest doesn't have a problem with number " + str(question_number))


@tree.command(name="team_answer_score",
              description="What your team has answered so far.")
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion)
async def team_answer_score(interaction, contest_name: str):
    contest = Contest.from_json(contest_name)
    team = contest.get_team_of_user(interaction.user.id)
    if team is not None:
        response_str = ""
        for question_num in team.answer_score.keys():
            response_str += "Question " + str(question_num) + ": Answered as " + str(
                team.answer_score[question_num]) + "\n"
        await interaction.response.send_message(response_str)
    else:
        await interaction.response.send_message("Hmmm... your team could not be found.")


@tree.command(name="team_answer_score_admin",
              description="Bot administrators only; gets the team answer with more admin-exclusive info.")
@discord.app_commands.autocomplete(contest_name=contest_name_autocompletion, team_name=all_team_names_autocompletion)
async def team_answer_score_admin(interaction, contest_name: str, team_name: str):
    contest = Contest.from_json(contest_name)
    team = contest.get_team(team_name)
    if team is not None:
        response_str = ""
        for question_num in team.answer_score.keys():
            point_val = team.answer_score[question_num]
            response_str += "Question " + str(question_num) + ":"
            if point_val > 0:
                response_str += "(marked as CORRECT) \n"
            else:
                response_str += "(marked as WRONG) \n"
        await interaction.response.send_message(response_str)
    else:
        await interaction.response.send_message("Hmmm... the team could not be found.")


def is_admin(interaction):
    return interaction.user.id in [614549755342880778, 757741186432630884]


@tree.command(name="sync",
              description="Bot administrators only; syncs the current slash commands.")
@discord.app_commands.check(is_admin)
async def sync_commands(interaction):
    await interaction.response.defer(thinking=True)
    await tree.sync(guild=discord.Object(id=current_guild_id))
    await interaction.followup.send("Commands synced.")


@tree.command(name="sync_global",
              description="Bot administrators only; syncs slash command on all servers.")
@discord.app_commands.check(is_admin)
async def sync_commands_globally(interaction):
    await interaction.response.defer(thinking=True)
    await tree.sync()
    await interaction.followup.send("Commands synced across all guilds.")

"""
db_group = discord.app_commands.Group(
    name="db",
    description="Bot administrators only; calls an action on the remote database.")


@db_group.command(name="get")  
@discord.app_commands.check(is_admin)
async def db_get(interaction, key: str):
    try:
        value = database.storage_api.get_value(key, evaluate=True)
        await interaction.response.send_message(str(value), ephemeral=True)
    except DataAPIException:
        await interaction.response.send_message(
            "DataAPIException. Are you sure the key exists?",
            ephemeral=True
        )


@db_group.command(name="set")  
@discord.app_commands.check(is_admin)
async def db_set(interaction, key: str, value: str):
    try:
        database.storage_api.set_value(key, value)
        await interaction.response.send_message(f"Set {key} to {value}.")
    except DataAPIException:
        await interaction.response.send_message(
            "DataAPIException.",
            ephemeral=True
        )


@db_group.command(name="del")  
@discord.app_commands.check(is_admin)
async def db_del(interaction, key: str):
    try:
        database.storage_api.del_value(key)
        await interaction.response.send_message(f"Deleted {key}.")
    except DataAPIException:
        await interaction.response.send_message(
            "DataAPIException. Are you sure the key exists?",
            ephemeral=True
        )


@db_group.command(name="keys")  
@discord.app_commands.check(is_admin)
async def db_keys(interaction):
    try:
        await interaction.response.send_message(
            str(database.storage_api.get_keys()),
            ephemeral=True
        )
    except DataAPIException:
        await interaction.response.send_message(
            "DataAPIException.",
            ephemeral=True
        )
"""


# DO NOT DELETE THESE LINES OF CODE:
#tree.add_command(db_group)
client.run(os.environ["token"])
