Feature: Shrug command access control

  Scenario: Admin can use shrug command
    Given a user with telegram user id 12345
    And the user is an admin
    And bot is initialized
    When the user calls "/shrug"
    Then the bot replies with "¯\\_(ツ)_/¯"

  Scenario: Non-admin cannot use shrug command
    Given a user with telegram user id 67890
    And the user is not an admin
    And bot is initialized
    When the user calls "/shrug"
    Then the bot doesn't reply

