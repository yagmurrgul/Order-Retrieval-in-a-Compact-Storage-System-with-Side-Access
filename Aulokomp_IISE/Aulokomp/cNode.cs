using System;
using System.Collections.Generic;
using System.Text;

namespace Aulokomp
{
    class cNode
    {

        public bool[] assigned;
        public int objVal;
        public cNode bestPrev;
        public int counter;
        public bool dominated;


        public cNode(bool[] a)
        {
            assigned = a;
            dominated = false;
        }

        public cNode(bool[] a, cNode bPrev)
        {
            assigned = a;
            bestPrev = bPrev;
            dominated = false;
            bestPrev.counter++;
        }

        public void killMe()
        {
            if (counter == 0)
            {
                assigned = null;
                bestPrev.counter--;
                bestPrev.killMe();
                bestPrev = null;
            }

        }

    }
}

