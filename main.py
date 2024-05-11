import requests
import csv
import json


def get_pr_data(owner, repo, pr_number):
    # GitHub API base URL
    base_url = "https://api.github.com"

    # Authentication
    headers = {
        "Authorization": "Bearer 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"
    }

    # Endpoint to get pull request details
    pull_request_url = f"{base_url}/repos/{owner}/{repo}/pulls/{pr_number}"

    # Send a GET request to fetch pull request details
    response = requests.get(pull_request_url, headers=headers)

    if response.status_code == 200:
        pull_request_data = response.json()

        # Extract pull request information
        title = pull_request_data["title"]
        body = pull_request_data["body"]
        author = pull_request_data.get("user", {}).get("login", "")

        # Endpoint to get files associated with the pull request
        files_url = pull_request_data["url"] + "/files"

        # Send a GET request to fetch files associated with the pull request
        files_response = requests.get(files_url, headers=headers)
        if files_response.status_code == 200:
            files_data = files_response.json()

            # Extract file information
            file_names = [file["filename"] for file in files_data]


        else:
            print("Failed to fetch files:", files_response.status_code)
    else:
        print("Failed to fetch pull request details:", response.status_code)
    return title, body, file_names, author


def setup_csv():
    # Specify the path to the CSV file
    csv_file = 'issues_data2.csv'
    # Define the CSV fieldnames
    fieldnames = ['Repository', 'Issue Number', 'Open Date', 'Closed Date', 'Issue Author', 'Issue Title', 'Issue Body',
                  'Comment Bodies', 'Comment Authors', 'Number of Comments', 'Labels', 'PR Number', 'PR Merge Date',
                  'PR Author', 'PR Title', 'PR Body', 'PR Files']
    # Writing data to CSV
    with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
    return csv_file


def generate_initial_query(owner_list, repo_list, repo_number):
    i = repo_number
    query = f"""query {{"""
    query += f"""
           repository{i}: repository(owner: "{owner_list[i]}", name: "{repo_list[i]}") {{
               issues(first: 100, states: CLOSED, orderBy: {{ field: CREATED_AT, direction: DESC }} ) {{
               pageInfo {{
                    endCursor
                    hasNextPage
                }}
                   nodes {{
                       number
                       createdAt
                       closedAt
                       title
                       author{{
                       login
                       }}
                       body
                       comments(first: 10) {{
                        totalCount
                        edges {{
                        node {{
                            author {{
                                login
                                        }}
                            body
                                }}
                            }}
                            }}
                       labels(first: 5) {{
                           nodes {{
                               name
                           }}
                       }}
                       timelineItems(itemTypes: [CLOSED_EVENT], first: 1) {{
                           nodes {{
                               ...on ClosedEvent {{
                                    closer{{
                                       ... on PullRequest {{
                                           number
                                           mergedAt
                                       }}
                                   }}
                               }}
                           }}
                       }}
                   }}
               }}
           }}
           """
    query += f"""}}"""
    return query


def generate_next_query(owner_list, repo_list, end_cursor, repo_number):
    i = repo_number
    query = f"""query {{"""
    query += f"""
              repository{i}: repository(owner: "{owner_list[i]}", name: "{repo_list[i]}") {{
                  issues(first: 100, states: CLOSED, orderBy: {{ field: CREATED_AT, direction: DESC }}, after: "{end_cursor}" ) {{
                   pageInfo {{
                    endCursor
                    hasNextPage
                }}
                      nodes {{
                          number   
                          createdAt
                          closedAt
                          title
                          author{{
                          login
                          }}
                          body
                          comments(first: 10) {{
                        totalCount
                        edges {{
                        node {{
                            author {{
                                login
                                        }}
                            body
                                }}
                            }}
                            }}
                          labels(first: 5) {{
                              nodes {{
                                  name
                              }}
                          }}
                          timelineItems(itemTypes: [CLOSED_EVENT], first: 1) {{
                           nodes {{
                               ...on ClosedEvent {{
                                    closer{{
                                       ... on PullRequest {{
                                           number
                                           mergedAt
                                       }}
                                   }}
                               }}
                           }}
                       }}
                      }}
                  }}
              }}
              """
    query += f"""}}"""
    return query


def data_extract(owner_list, repo_list, token, number_of_requests, csv_file):
    i = 0
    j = 100
    while i < len(repo_list):
        query = generate_initial_query(owner_list, repo_list, i)
        headers = {
            'Authorization': 'Bearer ' + token
        }

        # Send the request to GitHub GraphQL API
        response = requests.post('https://api.github.com/graphql', json={'query': query}, headers=headers)
        print(response.text)
        data = response.json()['data']
        write_to_csv(data, csv_file)

        # Extract endCursor
        end_cursor = data[f'repository{i}']['issues']['pageInfo']['endCursor']

        while j < number_of_requests[i]:
            query = generate_next_query(owner_list, repo_list, end_cursor, i)
            response = requests.post('https://api.github.com/graphql', json={'query': query}, headers=headers)
            data = response.json()['data']
            print(response.text)
            write_to_csv(data, csv_file)
            end_cursor = data[f'repository{i}']['issues']['pageInfo']['endCursor']
            j += 100
        i += 1

    return


def write_to_csv(data, csv_file):
    fieldnames = ['Repository', 'Issue Number', 'Open Date', 'Closed Date', 'Issue Author', 'Issue Title', 'Issue Body',
                  'Comment Bodies', 'Comment Authors', 'Number of Comments', 'Labels', 'PR Number', 'PR Merge Date', 'PR Author',
                  'PR Title', 'PR Body', 'PR Files']

    with open(csv_file, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        # Iterate over repositories in the data
        for repo_name, repo_data in data.items():
            issues = repo_data.get('issues', {}).get('nodes', [])

            # Write issues for each repository
            for issue in issues:
                closed_event = issue.get('timelineItems', {}).get('nodes', [{}])[0].get('closer', {})
                comments = issue.get('comments', {}).get('totalCount', 0)
                if closed_event:
                    pr_number = closed_event.get('number')
                    pr_merge_date = closed_event.get('mergedAt')
                    pr_title, pr_body, pr_file, pr_author = get_pr_data("JabRef", "jabref", pr_number)
                    max_length = 30000
                    comment_authors = '|SEPARATOR|'.join([comment_edge['node']['author']['login'] for comment_edge in
                                                          issue.get('comments', {}).get('edges', []) if
                                                          comment_edge.get('node', {}).get('author')])
                    comment_bodies = ""
                    issue_body = issue.get('body')
                    if len(issue_body) > 30000:
                        issue_body = issue_body[:max_length]

                    if issue.get('author') is not None:
                        # Extracting issue author's login
                        issue_author_login = issue['author'].get('login', '')
                    else:
                        issue_author_login = ''

                    for comment_edge in issue.get('comments', {}).get('edges', []):
                        body = comment_edge['node']['body']
                        if len(comment_bodies) + len(body) < max_length:
                            comment_bodies += body
                            comment_bodies += '|SEPARATOR|'
                    writer.writerow({
                        'Repository': repo_name,
                        'Open Date': issue.get('createdAt'),
                        'Closed Date': issue.get('closedAt'),
                        'Issue Number': issue.get('number'),
                        'Issue Title': issue.get('title'),
                        'Issue Body': issue_body,
                        'Number of Comments': issue.get('comments', {}).get('totalCount', 0),
                        'Labels': ', '.join([label.get('name', '') for label in issue.get('labels', {}).get('nodes', [])]),
                        'Comment Bodies': comment_bodies,
                        'Comment Authors': comment_authors,
                        'PR Number': pr_number,
                        'PR Merge Date': pr_merge_date,
                        'Issue Author': issue_author_login,
                        'PR Title': pr_title,
                        'PR Body': pr_body,
                        'PR Files': str(pr_file),
                        'PR Author': pr_author
                    })

    print(f'Data has been written to {csv_file}.')


csv_file = setup_csv()

# Read JSON data from the file
with open('conf.json', 'r') as file:
    config_data = json.load(file)

# Extract data from the JSON object
owner_list = config_data['owners']
repo_list = config_data['repositories']
access_token = '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'
number_of_requests = config_data['number_of_requests']


data = data_extract(owner_list, repo_list, access_token, number_of_requests, csv_file)
