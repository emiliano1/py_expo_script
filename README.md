# Example Export Script

## Installing Dependencies

All dependencies are put in the `requirements.txt` file in the src directory and then
run the following command to install them in this directory prior to uploading
the code.

    $ pip install -r requirements.txt -t /full/path/to/this/code

This will install all of the dependencies inside the code directory so they can
be bundled with your own code and deployed to Lambda.



### Initially coded in Python
##### A few comments and questions:
- we run a Javascript stack! This doesn't really showcase your Javascript ability :(
- could you talk through some of your thought process? What kind of pub/sub scenario were you aiming to support? What is a real world use case for this design? What design considerations / tradeoffs / alternatives did you consider and reject in favor of the design you settled on?
- how do I try this out?

##### Code Specific Questions:
- what are the table schemas?
- why did you choose to embed the subscribers into the event itself?
- from what I see, there are no event topics. Everyone subscribes to all events. Is that right?
- are events delivered in order per subscription? From what I see, if it fails to deliver event 1 to some subscriber, it will then attempt to deliver event 2 to the same subscriber. Also, as far as i'm aware, dynamodb scan returns results in arbitrary order, so you may be delivering events in arbitrary order!
- will you really scan the whole events table every time on every scheduled call (once per hr), and the whole subscribers table on every published event?
- am i right that the backoff pattern is linear: try once, wait an hour, try again?
---
##### Answers
- I coded on python since it was not specified. I thought any OOP language would work just fine. I can easily do this in JS but it will take me another 1-2 hours to redo it all.
- You need to install the dependencies on the src folder and then you can deploy it on AWS, you also have to create the tables on dynamoDB (like the readme file explains).

1. Table `events` has 3 columns of type `String`.
- `event` is the event the lambda receives to be send to the subscribers;
- `subscriber` is the endpoint to where the event is supposed to be send;
- `created_at` is the date and time at which the event was first tried to deliver and fail
The other table is the `subscribers` table and I assume it would have a `String` field that I called `endpoint` to which the event is supposed to be send.

##### Thought Process: 
The scenario that I was aiming would be to receive events from somewhere, most likely a system of ours that need to inform clients of some sort of event. The clients would be registered within the system and each would have an endpoint URL to which the event needs to be send to. The event is to be sent to everyone. The best way to use it would be to inform all registered clients of new things on the system, or something like that. It's a broadcast type of event. Kind of like a newsletter.

----- 

##### CODE SPECIFIC:
1. There are 2 tables. `events` and `subscribers`. 
2. The subscribers were not embedded into the event.
3. That could be an improvement, to have types of events and who is subscribed to it. But since this was just an exercise and event types were not described on the exercise I just assumed it would handle just 1 type of event and that it would be sent to all subscribers.
4. There was no requirement establishing the order at which the events should be delivered, so that was not done.
5. The table subscribers will be scanned every time an event needs to be published, since we need them to deliver the events to them. The table events contain only the events that failed to be delivered, so this table will be scanned every 1h to try and deliver the events. When they are delivered, the registers are removed. This was done in a way to not expand the table too much. If it is needed, another table can be added to save all the events and if they were delivered or not, just for information purposes.
6. Yes

---
---
---

## Altered to Node.JS
### I decided to just make the port of the codes I did to Node.js.

---
###### Questions:
1. If you do, could I suggest a couple of changes? Imagine your service is a broker for transactional messages on different topics, e.g. "fin:purchase", "user:new", "user:online". Those messages must be delivered in order by topic per subscriber. The events should be delivered with retry and backoff.

2. If you don't feel like taking the code further than the port to Node.js, can you explain what changes would be necessary to adapt to the above scenario? E.g. how would the table schemas need to change (if they do)?

3. Also, could you describe how you typically test/debug your lambda functions?

---
###### ANSWERS
###### If I had to change it to support the changes you want I would:
1. First replace the created_at column from String to number, and on it I would store the timestamp of the date-time at which the event was fired. This way I could use it to order the events and send it following the right order.

2. Then I would add another table to dynamoDB where I would store the types of events that are available (e.g. user:new). That table would also contain the list of subscribers that are subscribed to each type of event, this way I would only deliver the events to the subscribers that want it.

3. With the changes on the dynamoDB in place, in the codes instead of trying to deliver the event right when it arrives, it would first be stored in the table events, and older events would be tried to deliver again, before sending the new event. If a event fails for a subscriber, I would retry 3 times and back-off without trying any other event of that type for that subscriber, since it must follow order.

###### As for testing: 
Those codes I'm sending I did not had the time to test, but usually I create test files to do unit-test using mock. But unit-test and mock can only point to coding errors. Even when the codes are good, it may still not behave as it should if the response from APIs and other things are different. So, I usually test it on an sandbox account on AWS. At least that was what I did when I worked with lambdas. Companies provided a sandbox account that I could use for testing.
