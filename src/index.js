import express from 'express'; // Imports Express.js.
import reminderRoutes from './routes/remindersRoutes.js';
import errorHandlerMiddleware from './middlewares/errorHandlerMiddleware.js';

const app = express() // Creates an Express application instance.
const port = process.env.PORT || 3000

app.use(express.json())
app.use('/reminders', reminderRoutes)

app.use(errorHandlerMiddleware)

app.listen(port, () => {
  console.log(`Example app listening on port ${port}`)
}) // Starts the server on port 3000 and logs a confirmation message.