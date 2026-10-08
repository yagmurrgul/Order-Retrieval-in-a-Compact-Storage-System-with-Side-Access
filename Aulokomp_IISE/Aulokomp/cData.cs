using System;
using System.Collections.Generic;
using System.Text;
using System.Collections;
using System.IO;



namespace Aulokomp
{
    class cData
    {


        public static int NO_PINNING = 1;
        public static int PINNING = 0;

        public static int mode;
        public static int instanceNr;
        public static int num_Columns;
        public static int max_Height;
        public static double occupancy;
        public static int num_Boxes;
        public static bool[][] boxes;


        public static int[] colHeight;

        public static int[] boxColumn;
        public static int[] boxHeight;

        public static List<int>[] boxByColumn;
        public static List<int>[][] boxObj;

        public static Random rng;

        public cData()
        {
            //
            // TODO: Fügen Sie hier die Konstruktorlogik hinzu
            //
        }

        public static void initMe(Random r)
        {
            killMe();
            instanceNr = 0;
            rng = r;

        }


        public static void killMe()
        {
            colHeight = null;
            boxHeight = null;
            boxColumn = null;
            rng = null;

            if (boxByColumn != null) {
                for (int i = 0; i < num_Columns; i++)
                {
                    boxByColumn[i].Clear();
                    boxByColumn[i] = null;
                }
                boxByColumn = null;
            }

        }

     

        public static void randomizeHeights()
        {
            int numBoxes;
            int col;
            colHeight = new int[num_Columns];

            numBoxes = (int)Math.Floor(num_Columns * max_Height * occupancy);

            for (int i = 0; i < numBoxes;i++) {
                do
                {
                    col = rng.Next(num_Columns);
                } while (colHeight[col] == max_Height); 

                colHeight[col]++;
            }
        }

        public static void randomizeBoxes()
        {

            bool flag;
            bool accesible;
            int boxCount;

            boxes = new bool[num_Columns][];
            for (int i = 0; i < num_Columns; i++)
            {
                boxes[i] = new bool[colHeight[i]];
            }

            boxColumn = new int[num_Boxes];
            boxHeight = new int[num_Boxes];
            //rejection sampling for unique positions
            for (int i = 0; i < num_Boxes; i++)
            {
                flag = true;
                do
                {
                    do
                        boxColumn[i] = rng.Next(num_Columns);
                    while (colHeight[boxColumn[i]] == 0);

                    boxHeight[i] = rng.Next(colHeight[boxColumn[i]]);

                    if (!boxes[boxColumn[i]][boxHeight[i]])
                    {
                        boxCount = 0;
                        for (int j = 0; j < colHeight[boxColumn[i]]; j++)
                        {
                            if (boxes[boxColumn[i]][j])
                            {
                                boxCount++;
                            }
                        }
                        accesible = true;
                        for (int j = 0; j < boxColumn[i]; j++)
                        {
                            if (colHeight[j] - 1 < boxHeight[i] - boxCount)
                            {
                                accesible = false;
                                break;
                            }
                        }

                        if (accesible)
                        {
                            boxes[boxColumn[i]][boxHeight[i]] = true;
                            flag = false;
                        }

                    }
                } while (flag);
            }

            orderBoxByColumn();
            calculateObjectives();

        }


        private static void orderBoxByColumn()
        {
            int index;

            boxByColumn = new List<int>[num_Columns];

            for (int i = 0; i < num_Columns; i++)
            {
                boxByColumn[i] = new List<int>();
            }

            for (int i = 0; i < num_Boxes; i++)
            {
                index = 0;
                for (int j = 0; j < boxByColumn[boxColumn[i]].Count; j++)
                {
                    if (boxHeight[i] < boxHeight[boxByColumn[boxColumn[i]][j]])
                    {
                        break;
                    }
                    index++;
                }
                boxByColumn[boxColumn[i]].Insert(index, i);
            }

        }

        private static void calculateObjectives()
        {
            boxObj = new List<int>[num_Boxes][];
            int pred;
            int[] obj;

            for (int i = 0; i < num_Boxes; i++)

            {
                boxObj[i] = new List<int>[boxColumn[i] + 1];

                for (int j = 0; j < boxColumn[i] + 1; j++)
                {

                    boxObj[i][j] = new List<int>();
                }
                pred = 0;
                for (int k = 0; k < boxByColumn[boxColumn[i]].Count; k++)
                {
                    if (boxByColumn[boxColumn[i]][k] != i)
                    {
                        pred++;
                    }
                    else
                    {
                        break;
                    }
                }

                for (int k = 0; k <= pred; k++)
                {
                    obj = new int[boxColumn[i] + 1];
                    for (int l = 0; l < boxColumn[i]; l++)
                    {
                        for (int m = 0; m <= l; m++)
                        {
                            obj[m] += Math.Max(colHeight[l] - boxHeight[i] + k, 0);
                        }


                    }


                    for (int l = 0; l < boxColumn[i] + 1; l++)
                    {
                        obj[l] += colHeight[boxColumn[i]] - boxHeight[i] - 1;
                        boxObj[i][l].Insert(0, obj[l]);
                    }
                }
            }
        }

        public static void writeInstanceToFile(int large)
        {
            StreamWriter writer;

            if (large == 0)
            {
                writer = new StreamWriter("Instance_" + instanceNr.ToString(), false);
            }
            else {
                writer = new StreamWriter("Instance_" + instanceNr.ToString() + "_large.txt", false);
            }
            int mHeight = 0;

            for (int i = 0; i < num_Columns; i++)
            {
                if (mHeight < colHeight[i])
                {
                    mHeight = colHeight[i];
                }


            }

            for (int j = mHeight-1; j >= 0; j--)
            {
                for (int i = 0; i < num_Columns; i++)
                {
               
                    if (boxes[i].Length -1 < j)
                    {
                        if (i > 0 && boxes[i-1].Length -1 >= j) {
                            writer.Write("|   ");
                        } else {
                            writer.Write("    ");
                        }
                        
                    }
                    else if (!boxes[i][j])
                    {
                        if (i < num_Columns - 1)
                        {
                            writer.Write("|_0_");
                        }
                        else {
                            writer.Write("|_0_|");
                        }
                        
                        
                    }
                    else
                    {
                        if (i < num_Columns - 1)
                        {
                            writer.Write("|_1_");
                        }
                        else {
                            writer.Write("|_1_|");
                        }
                    
                    }
                }
                writer.WriteLine();
            }
            writer.Close();
        }

        public static void readInstancefromFile(int instanceNr, int large)
        {
            StreamReader reader;
            if (large == 0)
            {
                reader = new StreamReader("Instance_" + instanceNr.ToString() + ".txt");

            }
            else {
                reader = new StreamReader("Instance_" + instanceNr.ToString() + "_large.txt");

            }
            String line = "";
            String sub = "";
            int cols = 0;
            int boxNo = 0;
            List<List<bool>> columns = new List<List<bool>>();


            line = reader.ReadLine();
            while (line != null) 
            {
                cols = line.Length / 4;

                for (int i = 0; i < cols; i++)
                {
                    sub = line.Substring(i * 4, 4);
                    if (columns.Count < i + 1)
                    {
                        columns.Add(new List<bool>());
                    }
                    
                    if (sub == "|_0_")
                    {
                        columns[i].Insert(0, false);
                    }
                    else if (sub == "|_1_")
                    {
                        boxNo++;
                        columns[i].Insert(0, true);
                    }
                }

                line = reader.ReadLine();
            }

            reader.Close();
            num_Columns = columns.Count;
            num_Boxes = boxNo;


            colHeight = new int[num_Columns];

            boxes = new bool[num_Columns][];

            boxColumn = new int[num_Boxes];
            boxHeight = new int[num_Boxes];


            boxNo = 0;
            for (int i = 0; i < num_Columns; i++)
            {
                colHeight[i] = columns[i].Count;
                if (max_Height < colHeight[i]) {
                    max_Height = colHeight[i];
                }
                boxes[i] = new bool[colHeight[i]];
                for (int j = 0; j < colHeight[i]; j++)
                {
                    boxes[i][j] = columns[i][j];

                    if (boxes[i][j])
                    {
                        boxColumn[boxNo] = i;
                        boxHeight[boxNo] = j;
                        boxNo++;
                    }


                }
            }

            orderBoxByColumn();
            calculateObjectives();
        }

        public static void writeResults(String fileName, int instance, int objective, long states, double time)
        {
            StreamWriter writer = new StreamWriter(fileName,true);


            writer.WriteLine(instance.ToString() + " " + objective.ToString() + " " + states.ToString() + " " + time.ToString());

            writer.Close();
        }
    }
}
